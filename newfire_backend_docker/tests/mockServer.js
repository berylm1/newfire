/**
 * Mock Backend Server for Testing
 * 
 * This is a minimal mock implementation of the NewFire backend API
 * for testing the tenant/RBAC test harness without requiring a real backend.
 * 
 * Features:
 * - In-memory storage for test data
 * - Full JWT authentication simulation
 * - Tenant isolation enforcement
 * - All CRUD operations for companies, agents, and conversations
 * 
 * Usage:
 *   node mockServer.js
 *   # Then run tests with TEST_API_URL=http://localhost:3201
 */

import http from 'http';
import crypto from 'crypto';

// Configuration
const PORT = process.env.MOCK_PORT || 3201;
const JWT_SECRET = process.env.JWT_SECRET || 'test-jwt-secret-for-testing-only';

// In-memory database
const db = {
  users: new Map(),
  companies: new Map(),
  agents: new Map(),
  conversations: new Map(),
  sequences: {
    users: 1,
    companies: 1,
    agents: 1,
    conversations: 1,
  },
};

// Utility functions
function generateId(type) {
  const id = db.sequences[type]++;
  return id;
}

function generateAgentId(name) {
  return name.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now();
}

function generateToken(user) {
  const payload = {
    userId: user.id,
    email: user.email,
    role: user.role,
    companyId: user.company_id || null,
  };
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64');
  const signature = crypto.createHmac('sha256', JWT_SECRET)
    .update(`${header}.${body}`)
    .digest('base64');
  return `${header}.${body}.${signature}`;
}

function verifyToken(token) {
  try {
    const [header, body, signature] = token.split('.');
    const expectedSignature = crypto.createHmac('sha256', JWT_SECRET)
      .update(`${header}.${body}`)
      .digest('base64');
    if (signature !== expectedSignature) {
      throw new Error('Invalid signature');
    }
    return JSON.parse(Buffer.from(body, 'base64').toString());
  } catch {
    throw new Error('Invalid token');
  }
}

function hashPassword(password) {
  return crypto.createHash('sha256').update(password).digest('hex');
}

function comparePassword(password, hash) {
  return hashPassword(password) === hash;
}

function getUserFromRequest(req) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  const token = authHeader.slice(7);
  try {
    return verifyToken(token);
  } catch {
    return null;
  }
}

function requireAuth(req) {
  const user = getUserFromRequest(req);
  if (!user) {
    throw { status: 401, message: 'Unauthorized' };
  }
  return user;
}

function jsonResponse(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function errorResponse(res, status, message) {
  jsonResponse(res, status, { error: message });
}

// Request handler
async function handleRequest(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const path = url.pathname;
  const method = req.method;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  try {
    // Health check
    if (path === '/health' && method === 'GET') {
      jsonResponse(res, 200, { status: 'ok', service: 'newfire-backend-mock', version: '1.0.0' });
      return;
    }

    // Auth routes
    if (path === '/auth/signup' && method === 'POST') {
      const body = await parseBody(req);
      const { email, password, name } = body;

      if (!email || !password || !name) {
        return errorResponse(res, 400, 'Missing required fields');
      }

      // Check for duplicate email
      const existingUser = Array.from(db.users.values()).find(u => u.email === email);
      if (existingUser) {
        return errorResponse(res, 400, 'Email already exists');
      }

      const user = {
        id: generateId('users'),
        email,
        password_hash: hashPassword(password),
        name,
        role: 'user',
        onboarded: false,
        company_id: null,
        created_at: new Date().toISOString(),
      };
      db.users.set(user.id, user);

      const token = generateToken(user);
      jsonResponse(res, 201, {
        token,
        user: { id: user.id, email: user.email, name: user.name, role: user.role },
      });
      return;
    }

    if (path === '/auth/login' && method === 'POST') {
      const body = await parseBody(req);
      const { email, password } = body;

      const user = Array.from(db.users.values()).find(u => u.email === email);
      if (!user || !comparePassword(password, user.password_hash)) {
        return errorResponse(res, 401, 'Invalid credentials');
      }

      const token = generateToken(user);
      jsonResponse(res, 200, {
        token,
        user: { id: user.id, email: user.email, name: user.name, role: user.role, company_id: user.company_id },
      });
      return;
    }

    if (path === '/auth/me' && method === 'GET') {
      const user = requireAuth(req);
      const fullUser = db.users.get(user.userId);
      if (!fullUser) {
        return errorResponse(res, 404, 'User not found');
      }
      jsonResponse(res, 200, {
        id: fullUser.id,
        email: fullUser.email,
        name: fullUser.name,
        role: fullUser.role,
        company_id: fullUser.company_id,
      });
      return;
    }

    // Company routes
    if (path === '/companies' && method === 'GET') {
      const authUser = requireAuth(req);
      const companies = Array.from(db.companies.values())
        .filter(c => c.user_id === authUser.userId || authUser.role === 'admin');
      jsonResponse(res, 200, companies);
      return;
    }

    if (path === '/companies' && method === 'POST') {
      const authUser = requireAuth(req);
      const body = await parseBody(req);
      const { name, description } = body;

      if (!name) {
        return errorResponse(res, 400, 'Company name is required');
      }

      const company = {
        id: generateId('companies'),
        user_id: authUser.userId,
        name,
        description: description || '',
        created_at: new Date().toISOString(),
      };
      db.companies.set(company.id, company);

      // Associate user with company
      const user = db.users.get(authUser.userId);
      if (user) {
        user.company_id = company.id;
      }

      jsonResponse(res, 201, company);
      return;
    }

    if (path.startsWith('/companies/') && method === 'GET') {
      const authUser = requireAuth(req);
      const companyId = parseInt(path.split('/')[2]);
      const company = db.companies.get(companyId);

      if (!company) {
        return errorResponse(res, 404, 'Company not found');
      }

      if (company.user_id !== authUser.userId && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      jsonResponse(res, 200, company);
      return;
    }

    if (path.startsWith('/companies/') && method === 'PUT') {
      const authUser = requireAuth(req);
      const companyId = parseInt(path.split('/')[2]);
      const company = db.companies.get(companyId);

      if (!company) {
        return errorResponse(res, 404, 'Company not found');
      }

      if (company.user_id !== authUser.userId && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      const body = await parseBody(req);
      Object.assign(company, body);
      jsonResponse(res, 200, company);
      return;
    }

    if (path.startsWith('/companies/') && method === 'DELETE') {
      const authUser = requireAuth(req);
      const companyId = parseInt(path.split('/')[2]);
      const company = db.companies.get(companyId);

      if (!company) {
        return errorResponse(res, 404, 'Company not found');
      }

      if (authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Admin access required');
      }

      db.companies.delete(companyId);
      jsonResponse(res, 200, { success: true });
      return;
    }

    // Agent routes
    if (path === '/agents' && method === 'GET') {
      const authUser = requireAuth(req);
      const user = db.users.get(authUser.userId);
      
      if (!user || !user.company_id) {
        return errorResponse(res, 400, 'User has no company');
      }

      const agents = Array.from(db.agents.values())
        .filter(a => a.company_id === user.company_id);
      jsonResponse(res, 200, agents);
      return;
    }

    if (path === '/agents' && method === 'POST') {
      const authUser = requireAuth(req);
      const user = db.users.get(authUser.userId);

      if (!user || !user.company_id) {
        return errorResponse(res, 400, 'User has no company');
      }

      const body = await parseBody(req);
      const { name, description, role, system_prompt, model, provider } = body;

      const agent = {
        id: generateId('agents'),
        company_id: user.company_id,
        agent_id: generateAgentId(name || 'agent'),
        name: name || 'Unnamed Agent',
        role: role || null,
        description: description || null,
        system_prompt: system_prompt || null,
        model: model || 'gemma4:26b',
        provider: provider || 'local',
        icon: 'MessageSquare',
        color: 'from-blue-500 to-blue-600',
        status: 'active',
        created_at: new Date().toISOString(),
      };
      db.agents.set(agent.id, agent);
      jsonResponse(res, 201, agent);
      return;
    }

    if (path.startsWith('/agents/') && method === 'GET') {
      const authUser = requireAuth(req);
      const agentId = path.split('/')[2];
      const user = db.users.get(authUser.userId);
      const agent = Array.from(db.agents.values()).find(a => a.agent_id === agentId || a.id === parseInt(agentId));

      if (!agent) {
        return errorResponse(res, 404, 'Agent not found');
      }

      if (agent.company_id !== user?.company_id && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      jsonResponse(res, 200, agent);
      return;
    }

    if (path.startsWith('/agents/') && method === 'PUT') {
      const authUser = requireAuth(req);
      const agentId = path.split('/')[2];
      const user = db.users.get(authUser.userId);
      const agent = Array.from(db.agents.values()).find(a => a.agent_id === agentId || a.id === parseInt(agentId));

      if (!agent) {
        return errorResponse(res, 404, 'Agent not found');
      }

      if (agent.company_id !== user?.company_id && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      const body = await parseBody(req);
      Object.assign(agent, body);
      jsonResponse(res, 200, agent);
      return;
    }

    if (path.startsWith('/agents/') && method === 'DELETE') {
      const authUser = requireAuth(req);
      const agentId = path.split('/')[2];
      const user = db.users.get(authUser.userId);
      const agent = Array.from(db.agents.values()).find(a => a.agent_id === agentId || a.id === parseInt(agentId));

      if (!agent) {
        return errorResponse(res, 404, 'Agent not found');
      }

      if (agent.company_id !== user?.company_id && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      db.agents.delete(agent.id);
      jsonResponse(res, 200, { success: true });
      return;
    }

    // Chat route
    if (path === '/chat' && method === 'POST') {
      const authUser = requireAuth(req);
      const body = await parseBody(req);
      const { agentId, message } = body;

      const user = db.users.get(authUser.userId);
      const agent = Array.from(db.agents.values()).find(a => a.agent_id === agentId || a.id === parseInt(agentId));

      if (!agent) {
        return errorResponse(res, 404, 'Agent not found');
      }

      if (agent.company_id !== user?.company_id && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      // Create or update conversation
      const convKey = `${authUser.userId}-${agentId}`;
      let conversation = db.conversations.get(convKey);
      
      if (!conversation) {
        conversation = {
          id: generateId('conversations'),
          user_id: authUser.userId,
          agent_id: agentId,
          messages: [],
          updated_at: new Date().toISOString(),
        };
      }

      conversation.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      });

      // Mock response
      conversation.messages.push({
        role: 'assistant',
        content: `Mock response to: ${message}`,
        timestamp: new Date().toISOString(),
      });

      conversation.updated_at = new Date().toISOString();
      db.conversations.set(convKey, conversation);

      jsonResponse(res, 200, {
        message: conversation.messages[conversation.messages.length - 1].content,
        conversation,
      });
      return;
    }

    // Conversation route
    if (path.startsWith('/conversations/') && method === 'GET') {
      const authUser = requireAuth(req);
      const agentId = path.split('/')[2];
      const user = db.users.get(authUser.userId);
      const agent = Array.from(db.agents.values()).find(a => a.agent_id === agentId || a.id === parseInt(agentId));

      if (!agent) {
        return errorResponse(res, 404, 'Agent not found');
      }

      if (agent.company_id !== user?.company_id && authUser.role !== 'admin') {
        return errorResponse(res, 403, 'Access denied');
      }

      const convKey = `${authUser.userId}-${agentId}`;
      const conversation = db.conversations.get(convKey);
      jsonResponse(res, 200, conversation || { messages: [] });
      return;
    }

    // 404 for unknown routes
    errorResponse(res, 404, 'Not found');

  } catch (err) {
    if (err.status) {
      errorResponse(res, err.status, err.message);
    } else {
      console.error('Server error:', err);
      errorResponse(res, 500, 'Internal server error');
    }
  }
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

// Start server
const server = http.createServer(handleRequest);

server.listen(PORT, () => {
  console.log(`Mock NewFire Backend running on http://localhost:${PORT}`);
  console.log('Press Ctrl+C to stop');
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down mock server...');
  server.close(() => {
    console.log('Server stopped');
    process.exit(0);
  });
});