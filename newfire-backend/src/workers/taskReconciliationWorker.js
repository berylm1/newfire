/**
 * Task Reconciliation Worker
 * 
 * Backend worker that periodically reconciles active agent tasks (Paperclip/OpenHands/OpenClaw).
 * This ensures task completion events are emitted even if the frontend is not polling.
 * 
 * Features:
 * - Scheduled polling for active tasks
 * - Idempotent state transitions (timeout/blocked/done)
 * - Single emission of `agent.task.completed` events
 * - SLA metrics recording (queue time, total duration, terminal status)
 * - Tenant isolation
 */

const db = require('../db');
const webhooks = require('../webhooks');

// Task states
const TASK_STATES = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  TIMEOUT: 'timeout',
  BLOCKED: 'blocked',
  CANCELLED: 'cancelled'
};

// Terminal states that should not be reconciled
const TERMINAL_STATES = new Set([
  TASK_STATES.COMPLETED,
  TASK_STATES.FAILED,
  TASK_STATES.TIMEOUT,
  TASK_STATES.BLOCKED,
  TASK_STATES.CANCELLED
]);

// Agent types supported
const AGENT_TYPES = ['paperclip', 'openhands', 'openclaw'];

// Configuration defaults
const DEFAULT_CONFIG = {
  pollIntervalMs: 30000,        // 30 seconds
  taskTimeoutMs: 3600000,       // 1 hour default timeout
  maxRetries: 3,
  batchSize: 100,
  enabled: true
};

class TaskReconciliationWorker {
  constructor(config = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.intervalId = null;
    this.isRunning = false;
    this.lastRunTime = null;
    this.stats = {
      processed: 0,
      completed: 0,
      timedOut: 0,
      errors: 0
    };
  }

  /**
   * Start the reconciliation worker
   */
  start() {
    if (this.intervalId) {
      console.log('[TaskReconciliationWorker] Already running');
      return;
    }

    if (!this.config.enabled) {
      console.log('[TaskReconciliationWorker] Disabled by configuration');
      return;
    }

    console.log(`[TaskReconciliationWorker] Starting with poll interval: ${this.config.pollIntervalMs}ms`);
    
    // Run immediately, then schedule periodic runs
    this.runReconciliation();
    
    this.intervalId = setInterval(() => {
      this.runReconciliation();
    }, this.config.pollIntervalMs);
  }

  /**
   * Stop the reconciliation worker
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log('[TaskReconciliationWorker] Stopped');
    }
  }

  /**
   * Main reconciliation loop
   */
  async runReconciliation() {
    if (this.isRunning) {
      console.log('[TaskReconciliationWorker] Previous run still in progress, skipping');
      return;
    }

    this.isRunning = true;
    const startTime = Date.now();

    try {
      console.log('[TaskReconciliationWorker] Starting reconciliation cycle');
      
      // Get all active tasks grouped by tenant
      const activeTasks = await this.fetchActiveTasks();
      
      // Process each tenant's tasks
      const tenants = new Set(activeTasks.map(t => t.company_id));
      
      for (const tenantId of tenants) {
        const tenantTasks = activeTasks.filter(t => t.company_id === tenantId);
        await this.reconcileTenantTasks(tenantId, tenantTasks);
      }

      this.lastRunTime = new Date();
      console.log(`[TaskReconciliationWorker] Cycle completed in ${Date.now() - startTime}ms, processed ${this.stats.processed} tasks`);

    } catch (error) {
      console.error('[TaskReconciliationWorker] Reconciliation cycle failed:', error);
      this.stats.errors++;
    } finally {
      this.isRunning = false;
    }
  }

  /**
   * Fetch active tasks that need reconciliation
   */
  async fetchActiveTasks() {
    const query = `
      SELECT 
        id,
        company_id,
        agent_type,
        external_task_id,
        status,
        created_at,
        started_at,
        updated_at,
        completed_at,
        result_url,
        error_message
      FROM agent_tasks
      WHERE status IN ($1, $2, $3)
      AND agent_type = ANY($4)
      ORDER BY created_at ASC
      LIMIT $5
    `;
    
    const values = [
      TASK_STATES.PENDING,
      TASK_STATES.RUNNING,
      TASK_STATES.BLOCKED,
      AGENT_TYPES,
      this.config.batchSize
    ];

    try {
      const result = await db.query(query, values);
      return result.rows;
    } catch (error) {
      console.error('[TaskReconciliationWorker] Failed to fetch active tasks:', error);
      return [];
    }
  }

  /**
   * Reconcile tasks for a specific tenant
   */
  async reconcileTenantTasks(tenantId, tasks) {
    console.log(`[TaskReconciliationWorker] Reconciling ${tasks.length} tasks for tenant ${tenantId}`);

    for (const task of tasks) {
      try {
        await this.reconcileTask(task);
        this.stats.processed++;
      } catch (error) {
        console.error(`[TaskReconciliationWorker] Failed to reconcile task ${task.id}:`, error);
        this.stats.errors++;
      }
    }
  }

  /**
   * Reconcile a single task - main idempotent logic
   */
  async reconcileTask(task) {
    // Check if task is in terminal state - skip if already processed
    if (TERMINAL_STATES.has(task.status)) {
      return;
    }

    // Check for timeout
    const timeoutResult = await this.checkAndMarkTimeout(task);
    if (timeoutResult.timedOut) {
      this.stats.timedOut++;
      return;
    }

    // Check external agent for completion
    const completionResult = await this.checkExternalCompletion(task);
    
    if (completionResult.isCompleted) {
      await this.markTaskCompleted(task, completionResult.result);
      this.stats.completed++;
    } else if (completionResult.isFailed) {
      await this.markTaskFailed(task, completionResult.error);
    }
  }

  /**
   * Check if task has exceeded timeout threshold
   */
  async checkAndMarkTimeout(task) {
    const timeoutMs = this.config.taskTimeoutMs;
    const elapsed = Date.now() - new Date(task.started_at || task.created_at).getTime();

    if (elapsed > timeoutMs && !TERMINAL_STATES.has(task.status)) {
      console.log(`[TaskReconciliationWorker] Task ${task.id} timed out after ${elapsed}ms`);
      
      await this.updateTaskStatus(task.id, TASK_STATES.TIMEOUT, {
        error_message: `Task exceeded maximum duration of ${timeoutMs}ms`
      });

      // Emit timeout event
      await this.emitTaskEvent(task, 'agent.task.timeout', {
        duration_ms: elapsed,
        timeout_ms: timeoutMs
      });

      return { timedOut: true };
    }

    return { timedOut: false };
  }

  /**
   * Check external agent API for task completion status
   */
  async checkExternalCompletion(task) {
    const agentEndpoints = this.getAgentEndpoint(task.agent_type);
    if (!agentEndpoints) {
      return { isCompleted: false, isFailed: false };
    }

    try {
      // Fetch task status from external agent
      const response = await this.fetchExternalTaskStatus(
        agentEndpoints.statusUrl,
        task.external_task_id
      );

      if (response.status === 'completed' || response.status === 'success') {
        return {
          isCompleted: true,
          result: response.result || response.output
        };
      }

      if (response.status === 'failed' || response.status === 'error') {
        return {
          isCompleted: false,
          isFailed: true,
          error: response.error || response.message
        };
      }

      return { isCompleted: false, isFailed: false };

    } catch (error) {
      console.error(`[TaskReconciliationWorker] External status check failed for task ${task.id}:`, error.message);
      return { isCompleted: false, isFailed: false };
    }
  }

  /**
   * Get external agent API endpoint configuration
   */
  getAgentEndpoint(agentType) {
    const endpoints = {
      paperclip: {
        baseUrl: process.env.PAPERCLIP_URL || 'http://localhost:8080',
        statusUrl: (taskId) => `${process.env.PAPERCLIP_URL}/api/tasks/${taskId}/status`
      },
      openhands: {
        baseUrl: process.env.OPENHANDS_URL || 'http://localhost:3000',
        statusUrl: (taskId) => `${process.env.OPENHANDS_URL}/api/tasks/${taskId}`
      },
      openclaw: {
        baseUrl: process.env.OPENCLAW_URL || process.env.OPENCLAW_GW_URL || 'http://localhost:18789',
        statusUrl: (taskId) => `${process.env.OPENCLAW_URL}/api/v1/tasks/${taskId}`
      }
    };

    return endpoints[agentType];
  }

  /**
   * Fetch task status from external agent API
   */
  async fetchExternalTaskStatus(statusUrl, externalTaskId) {
    const url = statusUrl(externalTaskId);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${process.env.OPENCLAW_TOKEN}`,
        'Content-Type': 'application/json'
      },
      signal: AbortSignal.timeout(10000) // 10 second timeout
    });

    if (!response.ok) {
      throw new Error(`External API returned ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Mark task as completed - idempotent operation
   */
  async markTaskCompleted(task, result) {
    // Use a transaction to ensure idempotency
    const client = await db.getClient();
    
    try {
      await client.query('BEGIN');

      // Check current status in a row lock
      const currentTask = await client.query(
        'SELECT status FROM agent_tasks WHERE id = $1 FOR UPDATE',
        [task.id]
      );

      // Idempotency check - only proceed if not already in terminal state
      if (TERMINAL_STATES.has(currentTask.rows[0]?.status)) {
        console.log(`[TaskReconciliationWorker] Task ${task.id} already in terminal state, skipping`);
        await client.query('ROLLBACK');
        return;
      }

      const completedAt = new Date();
      const startedAt = new Date(task.started_at || task.created_at);
      const totalDurationMs = completedAt.getTime() - startedAt.getTime();
      const queueTimeMs = startedAt.getTime() - new Date(task.created_at).getTime();

      // Update task with completion data
      await client.query(`
        UPDATE agent_tasks
        SET 
          status = $1,
          completed_at = $2,
          result_url = $3,
          duration_ms = $4,
          queue_time_ms = $5,
          updated_at = NOW()
        WHERE id = $6
      `, [
        TASK_STATES.COMPLETED,
        completedAt,
        result?.url || task.result_url,
        totalDurationMs,
        queueTimeMs,
        task.id
      ]);

      await client.query('COMMIT');

      // Emit completion event (only once per task)
      await this.emitTaskEvent(task, 'agent.task.completed', {
        result,
        duration_ms: totalDurationMs,
        queue_time_ms: queueTimeMs,
        completed_at: completedAt.toISOString()
      });

      console.log(`[TaskReconciliationWorker] Task ${task.id} marked completed`);

    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Mark task as failed - idempotent operation
   */
  async markTaskFailed(task, errorMessage) {
    const client = await db.getClient();
    
    try {
      await client.query('BEGIN');

      // Check current status with row lock
      const currentTask = await client.query(
        'SELECT status FROM agent_tasks WHERE id = $1 FOR UPDATE',
        [task.id]
      );

      // Idempotency check
      if (TERMINAL_STATES.has(currentTask.rows[0]?.status)) {
        console.log(`[TaskReconciliationWorker] Task ${task.id} already in terminal state, skipping`);
        await client.query('ROLLBACK');
        return;
      }

      const completedAt = new Date();
      const totalDurationMs = completedAt.getTime() - new Date(task.started_at || task.created_at).getTime();

      await client.query(`
        UPDATE agent_tasks
        SET 
          status = $1,
          completed_at = $2,
          error_message = $3,
          duration_ms = $4,
          updated_at = NOW()
        WHERE id = $5
      `, [
        TASK_STATES.FAILED,
        completedAt,
        errorMessage,
        totalDurationMs,
        task.id
      ]);

      await client.query('COMMIT');

      // Emit failure event
      await this.emitTaskEvent(task, 'agent.task.failed', {
        error: errorMessage,
        duration_ms: totalDurationMs
      });

      console.log(`[TaskReconciliationWorker] Task ${task.id} marked failed: ${errorMessage}`);

    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Update task status with SLA metrics
   */
  async updateTaskStatus(taskId, status, additionalFields = {}) {
    const fields = {
      status,
      updated_at: new Date(),
      ...additionalFields
    };

    if (status === TASK_STATES.COMPLETED || status === TASK_STATES.FAILED) {
      fields.completed_at = new Date();
      fields.duration_ms = Date.now() - new Date(fields.started_at).getTime();
    }

    const setClauses = Object.keys(fields).map((k, i) => `${k} = $${i + 2}`).join(', ');
    
    await db.query(`
      UPDATE agent_tasks
      SET ${setClauses}
      WHERE id = $1
    `, [taskId, ...Object.values(fields)]);
  }

  /**
   * Emit task event via webhook - ensures single emission
   */
  async emitTaskEvent(task, eventType, payload) {
    try {
      await webhooks.emitExternalEvent(
        task.company_id,
        eventType,
        {
          task_id: task.id,
          external_task_id: task.external_task_id,
          agent_type: task.agent_type,
          ...payload
        },
        { idempotency_key: `${eventType}:${task.id}` }
      );
    } catch (error) {
      console.error(`[TaskReconciliationWorker] Failed to emit ${eventType} for task ${task.id}:`, error);
    }
  }

  /**
   * Get worker statistics
   */
  getStats() {
    return {
      ...this.stats,
      isRunning: this.isRunning,
      lastRunTime: this.lastRunTime,
      config: this.config
    };
  }

  /**
   * Reset statistics
   */
  resetStats() {
    this.stats = {
      processed: 0,
      completed: 0,
      timedOut: 0,
      errors: 0
    };
  }
}

// Export singleton instance
const worker = new TaskReconciliationWorker();

module.exports = {
  TaskReconciliationWorker,
  worker,
  TASK_STATES,
  TERMINAL_STATES,
  AGENT_TYPES
};
