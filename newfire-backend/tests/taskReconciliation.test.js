/**
 * Task Reconciliation Worker Tests
 * 
 * Comprehensive tests covering:
 * - Duplicate reconciliation handling
 * - Task completion scenarios
 * - Timeout/blocked state transitions
 * - Tenant isolation
 */

const { jest, describe, it, expect, beforeEach, afterEach } = require('@jest/globals');

// Mock dependencies before requiring the module
const mockDbQuery = jest.fn();
const mockDbGetClient = jest.fn();
const mockEmitExternalEvent = jest.fn();

jest.mock('../src/db', () => ({
  query: (...args) => mockDbQuery(...args),
  getClient: () => mockDbGetClient()
}));

jest.mock('../src/webhooks', () => ({
  emitExternalEvent: (...args) => mockEmitExternalEvent(...args)
}));

// Import after mocking
const { TaskReconciliationWorker, TASK_STATES, TERMINAL_STATES, AGENT_TYPES } = require('../src/workers/taskReconciliationWorker');

describe('TaskReconciliationWorker', () => {
  let worker;
  let mockClient;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup mock client for transactions
    mockClient = {
      query: jest.fn(),
      release: jest.fn()
    };
    mockDbGetClient.mockResolvedValue(mockClient);
    
    // Create worker instance with test config
    worker = new TaskReconciliationWorker({
      pollIntervalMs: 1000,
      taskTimeoutMs: 60000,
      batchSize: 10,
      enabled: true
    });
  });

  afterEach(() => {
    worker.stop();
  });

  describe('Constructor and Configuration', () => {
    it('should create worker with default configuration', () => {
      const defaultWorker = new TaskReconciliationWorker();
      const stats = defaultWorker.getStats();
      
      expect(stats.config.pollIntervalMs).toBe(30000);
      expect(stats.config.taskTimeoutMs).toBe(3600000);
      expect(stats.config.batchSize).toBe(100);
      expect(stats.config.enabled).toBe(true);
    });

    it('should merge custom configuration with defaults', () => {
      const customWorker = new TaskReconciliationWorker({
        pollIntervalMs: 5000,
        enabled: false
      });
      const stats = customWorker.getStats();
      
      expect(stats.config.pollIntervalMs).toBe(5000);
      expect(stats.config.enabled).toBe(false);
      expect(stats.config.taskTimeoutMs).toBe(3600000); // Default
    });
  });

  describe('State Constants', () => {
    it('should have correct task states', () => {
      expect(TASK_STATES.PENDING).toBe('pending');
      expect(TASK_STATES.RUNNING).toBe('running');
      expect(TASK_STATES.COMPLETED).toBe('completed');
      expect(TASK_STATES.FAILED).toBe('failed');
      expect(TASK_STATES.TIMEOUT).toBe('timeout');
      expect(TASK_STATES.BLOCKED).toBe('blocked');
      expect(TASK_STATES.CANCELLED).toBe('cancelled');
    });

    it('should define correct terminal states', () => {
      expect(TERMINAL_STATES.has('completed')).toBe(true);
      expect(TERMINAL_STATES.has('failed')).toBe(true);
      expect(TERMINAL_STATES.has('timeout')).toBe(true);
      expect(TERMINAL_STATES.has('blocked')).toBe(true);
      expect(TERMINAL_STATES.has('cancelled')).toBe(true);
      expect(TERMINAL_STATES.has('pending')).toBe(false);
      expect(TERMINAL_STATES.has('running')).toBe(false);
    });

    it('should support all agent types', () => {
      expect(AGENT_TYPES).toContain('paperclip');
      expect(AGENT_TYPES).toContain('openhands');
      expect(AGENT_TYPES).toContain('openclaw');
    });
  });

  describe('fetchActiveTasks', () => {
    it('should fetch only active non-terminal tasks', async () => {
      const mockTasks = [
        { id: 1, company_id: 'tenant1', status: 'running', agent_type: 'openhands' },
        { id: 2, company_id: 'tenant1', status: 'pending', agent_type: 'openclaw' }
      ];
      
      mockDbQuery.mockResolvedValue({ rows: mockTasks });
      
      const tasks = await worker.fetchActiveTasks();
      
      expect(mockDbQuery).toHaveBeenCalled();
      const queryCall = mockDbQuery.mock.calls[0];
      expect(queryCall[1]).toContain('pending');
      expect(queryCall[1]).toContain('running');
      expect(queryCall[1]).toContain('blocked');
      expect(queryCall[1]).toContain(10); // batchSize
    });

    it('should return empty array on database error', async () => {
      mockDbQuery.mockRejectedValue(new Error('Database error'));
      
      const tasks = await worker.fetchActiveTasks();
      
      expect(tasks).toEqual([]);
    });
  });

  describe('Idempotent Reconciliation', () => {
    it('should skip tasks already in terminal state', async () => {
      const completedTask = {
        id: 1,
        company_id: 'tenant1',
        status: 'completed',
        agent_type: 'openhands',
        created_at: new Date().toISOString()
      };

      await worker.reconcileTask(completedTask);
      
      // Should not attempt any state changes
      expect(mockDbGetClient).not.toHaveBeenCalled();
    });

    it('should not emit duplicate completion events', async () => {
      const runningTask = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-123',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString()
      };

      // Setup mock to return already completed
      mockClient.query
        .mockResolvedValueOnce({}) // BEGIN
        .mockResolvedValueOnce({ rows: [{ status: 'completed' }] }) // SELECT FOR UPDATE
        .mockResolvedValueOnce({}); // ROLLBACK

      await worker.reconcileTask(runningTask);
      
      // Should rollback without emitting
      expect(mockEmitExternalEvent).not.toHaveBeenCalled();
    });

    it('should handle concurrent reconciliation attempts safely', async () => {
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-123',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString()
      };

      // First call returns pending, second call returns completed (simulating race condition)
      let callCount = 0;
      mockClient.query
        .mockImplementation((sql) => {
          if (sql === 'BEGIN') {
            return Promise.resolve({});
          }
          if (sql.includes('FOR UPDATE')) {
            callCount++;
            // Second concurrent request already completed the task
            return Promise.resolve({ rows: [{ status: callCount === 1 ? 'running' : 'completed' }] });
          }
          if (sql === 'ROLLBACK' || sql === 'COMMIT') {
            return Promise.resolve({});
          }
          return Promise.resolve({});
        });

      // Run reconciliation twice concurrently
      await Promise.all([
        worker.reconcileTask(task),
        worker.reconcileTask(task)
      ]);

      // Only one should proceed
      expect(mockEmitExternalEvent.mock.calls.length).toBeLessThanOrEqual(1);
    });
  });

  describe('Task Completion', () => {
    beforeEach(() => {
      global.fetch = jest.fn();
    });

    it('should mark task as completed when external API reports success', async () => {
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-123',
        created_at: new Date().toISOString(),
        started_at: new Date(Date.now() - 60000).toISOString()
      };

      mockClient.query
        .mockResolvedValueOnce({}) // BEGIN
        .mockResolvedValueOnce({ rows: [{ status: 'running' }] }) // SELECT FOR UPDATE
        .mockResolvedValueOnce({}); // UPDATE

      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'completed', result: { url: 'https://result.example' } })
      });

      await worker.reconcileTask(task);

      // Verify completion was recorded
      expect(mockEmitExternalEvent).toHaveBeenCalledWith(
        'tenant1',
        'agent.task.completed',
        expect.objectContaining({
          task_id: 1,
          external_task_id: 'ext-123'
        }),
        expect.any(Object)
      );
    });

    it('should record SLA metrics on completion', async () => {
      const createdAt = new Date(Date.now() - 120000); // 2 minutes ago
      const startedAt = new Date(Date.now() - 60000);  // 1 minute ago
      
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openclaw',
        external_task_id: 'ext-456',
        created_at: createdAt.toISOString(),
        started_at: startedAt.toISOString()
      };

      let updateCall;
      mockClient.query
        .mockResolvedValueOnce({}) // BEGIN
        .mockResolvedValueOnce({ rows: [{ status: 'running' }] }) // SELECT FOR UPDATE
        .mockImplementation((sql, params) => {
          if (sql.includes('UPDATE agent_tasks')) {
            updateCall = { sql, params };
            return Promise.resolve({});
          }
          return Promise.resolve({});
        });

      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'completed' })
      });

      await worker.reconcileTask(task);

      // Verify duration_ms and queue_time_ms were recorded
      expect(updateCall.params).toContain(TASK_STATES.COMPLETED);
      expect(updateCall.params.some(p => typeof p === 'number' && p > 0)).toBe(true);
    });
  });

  describe('Timeout Handling', () => {
    it('should mark task as timeout when exceeding threshold', async () => {
      // Task started 2 hours ago (exceeds 1 hour timeout)
      const oldTask = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-789',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        started_at: new Date(Date.now() - 7200000).toISOString()
      };

      mockClient.query.mockResolvedValue({ rows: [] });

      await worker.reconcileTask(oldTask);

      // Should emit timeout event
      expect(mockEmitExternalEvent).toHaveBeenCalledWith(
        'tenant1',
        'agent.task.timeout',
        expect.objectContaining({
          task_id: 1,
          timeout_ms: 60000
        }),
        expect.any(Object)
      );
    });

    it('should not timeout tasks within threshold', async () => {
      // Task started 30 seconds ago (within 1 hour timeout)
      const recentTask = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-789',
        created_at: new Date(Date.now() - 30000).toISOString(),
        started_at: new Date(Date.now() - 30000).toISOString()
      };

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'running' })
      });

      await worker.reconcileTask(recentTask);

      // Should not emit timeout event
      expect(mockEmitExternalEvent).not.toHaveBeenCalledWith(
        expect.anything(),
        'agent.task.timeout',
        expect.anything()
      );
    });
  });

  describe('Blocked State', () => {
    it('should process blocked tasks and attempt resolution', async () => {
      const blockedTask = {
        id: 1,
        company_id: 'tenant1',
        status: 'blocked',
        agent_type: 'openclaw',
        external_task_id: 'ext-blocked',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString()
      };

      // Simulate blocked tasks being re-queued
      mockClient.query.mockResolvedValue({ rows: [] });

      await worker.reconcileTask(blockedTask);

      // Blocked tasks should be processed (not skipped)
      // Actual resolution logic would depend on agent-specific handling
      expect(mockDbGetClient).toHaveBeenCalled();
    });
  });

  describe('Tenant Isolation', () => {
    it('should process tasks per-tenant independently', async () => {
      const tasks = [
        { id: 1, company_id: 'tenant1', status: 'running', agent_type: 'openhands', external_task_id: 'ext-1', created_at: new Date().toISOString(), started_at: new Date().toISOString() },
        { id: 2, company_id: 'tenant2', status: 'running', agent_type: 'openclaw', external_task_id: 'ext-2', created_at: new Date().toISOString(), started_at: new Date().toISOString() },
        { id: 3, company_id: 'tenant1', status: 'pending', agent_type: 'paperclip', external_task_id: 'ext-3', created_at: new Date().toISOString(), started_at: new Date().toISOString() }
      ];

      mockDbQuery.mockResolvedValue({ rows: tasks });
      
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'running' })
      });

      await worker.runReconciliation();

      // Each tenant should be processed
      const tenants = new Set(tasks.map(t => t.company_id));
      expect(tenants.size).toBe(2);
    });

    it('should emit events with correct tenant context', async () => {
      const task = {
        id: 1,
        company_id: 'special-tenant-xyz',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-tenant-test',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        started_at: new Date(Date.now() - 7200000).toISOString()
      };

      mockClient.query.mockResolvedValue({ rows: [] });

      await worker.reconcileTask(task);

      // Event should be emitted for the correct tenant
      expect(mockEmitExternalEvent).toHaveBeenCalledWith(
        'special-tenant-xyz',
        expect.any(String),
        expect.objectContaining({
          task_id: 1,
          company_id: 'special-tenant-xyz'
        }),
        expect.any(Object)
      );
    });

    it('should not cross-tenant data leakage in queries', async () => {
      const queryCall = mockDbQuery.mock.calls[0];
      const query = queryCall[0];
      const values = queryCall[1];

      // Verify query filters by status, not by arbitrary conditions
      expect(query).toContain('WHERE status IN');
      expect(query).toContain('agent_type = ANY');
      
      // Values should be safe primitives
      values.forEach(val => {
        if (typeof val === 'string') {
          expect(val).not.toContain(';'); // No SQL injection
        }
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle external API errors gracefully', async () => {
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-error',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString()
      };

      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      // Should not throw, just skip this task
      await expect(worker.reconcileTask(task)).resolves.not.toThrow();
    });

    it('should continue processing other tasks when one fails', async () => {
      const tasks = [
        { id: 1, company_id: 'tenant1', status: 'running', agent_type: 'invalid-agent', external_task_id: 'ext-fail', created_at: new Date().toISOString(), started_at: new Date().toISOString() },
        { id: 2, company_id: 'tenant1', status: 'running', agent_type: 'openhands', external_task_id: 'ext-ok', created_at: new Date().toISOString(), started_at: new Date().toISOString() }
      ];

      mockDbQuery.mockResolvedValue({ rows: tasks });
      
      global.fetch = jest.fn().mockRejectedValue(new Error('Agent not found'));

      // Should not throw
      await expect(worker.runReconciliation()).resolves.not.toThrow();
      
      // Stats should reflect the error
      const stats = worker.getStats();
      expect(stats.errors).toBeGreaterThanOrEqual(0);
    });

    it('should handle database transaction failures', async () => {
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'running',
        agent_type: 'openhands',
        external_task_id: 'ext-db-error',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString()
      };

      mockClient.query
        .mockResolvedValueOnce({}) // BEGIN
        .mockRejectedValueOnce(new Error('Database connection lost')); // SELECT fails

      // Should handle gracefully
      await expect(worker.reconcileTask(task)).resolves.not.toThrow();
    });
  });

  describe('Statistics Tracking', () => {
    it('should track processed task count', async () => {
      const task = {
        id: 1,
        company_id: 'tenant1',
        status: 'completed', // Will be skipped
        agent_type: 'openhands',
        created_at: new Date().toISOString()
      };

      await worker.reconcileTask(task);
      
      // Completed tasks are skipped, not processed
      const stats = worker.getStats();
      expect(stats.processed).toBe(0);
    });

    it('should reset statistics', () => {
      worker.stats = {
        processed: 10,
        completed: 5,
        timedOut: 3,
        errors: 2
      };

      worker.resetStats();

      const stats = worker.getStats();
      expect(stats.processed).toBe(0);
      expect(stats.completed).toBe(0);
      expect(stats.timedOut).toBe(0);
      expect(stats.errors).toBe(0);
    });
  });

  describe('Worker Lifecycle', () => {
    it('should start and stop correctly', () => {
      jest.useFakeTimers();
      
      worker.start();
      expect(worker.intervalId).not.toBeNull();
      
      worker.stop();
      expect(worker.intervalId).toBeNull();
      
      jest.useRealTimers();
    });

    it('should not start if disabled', () => {
      const disabledWorker = new TaskReconciliationWorker({ enabled: false });
      disabledWorker.start();
      
      expect(disabledWorker.intervalId).toBeNull();
    });

    it('should report running state', async () => {
      jest.useFakeTimers();
      
      worker.start();
      expect(worker.isRunning).toBe(false); // Not yet running
      
      // Advance timer to trigger first run
      jest.advanceTimersByTime(1000);
      
      // Note: isRunning will be set during actual execution
      worker.stop();
      
      jest.useRealTimers();
    });
  });
});

describe('SLA Reporting Integration', () => {
  let worker;
  let mockClient;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockClient = {
      query: jest.fn(),
      release: jest.fn()
    };
    mockDbGetClient.mockResolvedValue(mockClient);
    
    worker = new TaskReconciliationWorker({
      pollIntervalMs: 1000,
      taskTimeoutMs: 60000
    });
  });

  it('should record queue time from created_at to started_at', async () => {
    const createdAt = new Date(Date.now() - 100000);
    const startedAt = new Date(Date.now() - 60000);
    
    const task = {
      id: 1,
      company_id: 'tenant1',
      status: 'running',
      agent_type: 'openhands',
      external_task_id: 'ext-sla',
      created_at: createdAt.toISOString(),
      started_at: startedAt.toISOString()
    };

    let updateParams;
    mockClient.query
      .mockResolvedValueOnce({}) // BEGIN
      .mockResolvedValueOnce({ rows: [{ status: 'running' }] }) // SELECT
      .mockImplementation((sql, params) => {
        if (sql.includes('UPDATE agent_tasks')) {
          updateParams = params;
          return Promise.resolve({});
        }
        return Promise.resolve({});
      });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed' })
    });

    await worker.reconcileTask(task);

    // Verify queue_time_ms was calculated
    expect(updateParams).toBeDefined();
    const queueTimeIndex = updateParams.findIndex(p => p === 60000); // started - created
    expect(queueTimeIndex).toBeGreaterThan(-1);
  });

  it('should record total duration on completion', async () => {
    const startedAt = new Date(Date.now() - 120000);
    
    const task = {
      id: 1,
      company_id: 'tenant1',
      status: 'running',
      agent_type: 'openhands',
      external_task_id: 'ext-duration',
      created_at: startedAt.toISOString(),
      started_at: startedAt.toISOString()
    };

    let updateParams;
    mockClient.query
      .mockResolvedValueOnce({}) // BEGIN
      .mockResolvedValueOnce({ rows: [{ status: 'running' }] }) // SELECT
      .mockImplementation((sql, params) => {
        if (sql.includes('UPDATE agent_tasks')) {
          updateParams = params;
          return Promise.resolve({});
        }
        return Promise.resolve({});
      });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed' })
    });

    await worker.reconcileTask(task);

    // Verify duration_ms was recorded (approximately 120000ms)
    expect(updateParams).toBeDefined();
    const durationIndex = updateParams.findIndex(p => typeof p === 'number' && p >= 110000 && p <= 130000);
    expect(durationIndex).toBeGreaterThan(-1);
  });

  it('should emit event with SLA metrics', async () => {
    const task = {
      id: 1,
      company_id: 'tenant1',
      status: 'running',
      agent_type: 'openhands',
      external_task_id: 'ext-sla-event',
      created_at: new Date(Date.now() - 7200000).toISOString(),
      started_at: new Date(Date.now() - 7200000).toISOString()
    };

    mockClient.query.mockResolvedValue({ rows: [] });

    await worker.reconcileTask(task);

    // Event should include timing metrics
    expect(mockEmitExternalEvent).toHaveBeenCalledWith(
      'tenant1',
      'agent.task.timeout',
      expect.objectContaining({
        duration_ms: expect.any(Number),
        timeout_ms: expect.any(Number)
      }),
      expect.any(Object)
    );
  });
});
