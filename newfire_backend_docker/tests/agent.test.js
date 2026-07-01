/**
 * Agent Access Tests - Agent Creation and Access Tests
 * 
 * Tests cover:
 * - Agent creation within tenant scope
 * - Agent retrieval and listing
 * - Agent update and delete operations
 * - Tenant-scoped agent access (users only see their company's agents)
 * - Chat interactions with agents
 */

import { jest } from '@jest/globals';
import { TestClient, generateTestEmail, generateTestCompanyName, generateTestAgentName, DatabaseHelper } from './helpers/index.js';

describe('Agent - Creation', () => {
  let client;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    // Setup: Create user with company
    await client.signup(
      generateTestEmail('agentcreate'),
      'SecurePass123!',
      'Agent Creator'
    );
    await client.createCompany(generateTestCompanyName());
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should create an agent with valid data', async () => {
    const agentData = {
      name: generateTestAgentName(),
      description: 'Test agent description',
      role: 'assistant',
      system_prompt: 'You are a helpful test agent.',
      model: 'gemma4:26b',
      provider: 'local',
    };

    const agent = await client.createAgent(agentData);

    expect(agent).toBeDefined();
    expect(agent.id || agent.agent_id).toBeDefined();
    expect(agent.name).toBe(agentData.name);
    expect(agent.company_id || agent.companyId).toBe(client.companyId);
  });

  test('should create agent with minimal required fields', async () => {
    const agentData = {
      name: generateTestAgentName(),
    };

    const agent = await client.createAgent(agentData);

    expect(agent).toBeDefined();
    expect(agent.name).toBe(agentData.name);
    // Default values should be applied
    expect(agent.model).toBe('gemma4:26b');
    expect(agent.provider).toBe('local');
  });

  test('should auto-generate agent_id', async () => {
    const agentData = {
      name: 'My Test Agent',
    };

    const agent = await client.createAgent(agentData);

    expect(agent.agent_id).toBeDefined();
    expect(typeof agent.agent_id).toBe('string');
    expect(agent.agent_id.length).toBeGreaterThan(0);
  });

  test('should require authentication to create agent', async () => {
    const unauthenticatedClient = new TestClient();
    const agentData = { name: generateTestAgentName() };

    await expect(unauthenticatedClient.createAgent(agentData))
      .rejects.toThrow();
  });

  test('should require company to create agent', async () => {
    // User without company
    const client = new TestClient();
    await client.signup(
      generateTestEmail('nocompany'),
      'SecurePass123!',
      'No Company User'
    );

    const agentData = { name: generateTestAgentName() };
    await expect(client.createAgent(agentData))
      .rejects.toThrow();
  });

  test('should reject agent creation with empty name', async () => {
    const agentData = { name: '' };

    await expect(client.createAgent(agentData))
      .rejects.toThrow();
  });

  test('should set agent status to active by default', async () => {
    const agent = await client.createAgent({ name: generateTestAgentName() });

    expect(agent.status).toBe('active');
  });

  test('should allow custom agent configuration', async () => {
    const agentData = {
      name: generateTestAgentName(),
      model: 'glm4:9b',
      provider: 'openrouter',
      icon: 'Bot',
      color: 'from-green-500 to-green-600',
      system_prompt: 'You are a specialized coding assistant.',
    };

    const agent = await client.createAgent(agentData);

    expect(agent.model).toBe('glm4:9b');
    expect(agent.provider).toBe('openrouter');
    expect(agent.icon).toBe('Bot');
    expect(agent.color).toBe('from-green-500 to-green-600');
  });
});

describe('Agent - Retrieval', () => {
  let client;
  let createdAgent;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    // Setup
    await client.signup(
      generateTestEmail('agentget'),
      'SecurePass123!',
      'Agent Get User'
    );
    await client.createCompany(generateTestCompanyName());
    
    // Create an agent to retrieve
    createdAgent = await client.createAgent({
      name: generateTestAgentName(),
      description: 'Test retrieval agent',
    });
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should get agent by ID', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    const agent = await client.getAgent(agentId);

    expect(agent).toBeDefined();
    expect(agent.id || agent.agent_id).toBe(agentId);
  });

  test('should list all agents for company', async () => {
    // Create additional agents
    await client.createAgent({ name: generateTestAgentName() });
    await client.createAgent({ name: generateTestAgentName() });

    const agents = await client.listAgents();

    expect(agents).toBeDefined();
    expect(Array.isArray(agents)).toBe(true);
    expect(agents.length).toBe(3);
  });

  test('should include agent details in list', async () => {
    const agents = await client.listAgents();

    agents.forEach(agent => {
      expect(agent.id || agent.agent_id).toBeDefined();
      expect(agent.name).toBeDefined();
      expect(agent.company_id || agent.companyId).toBe(client.companyId);
    });
  });

  test('should reject access without authentication', async () => {
    const unauthenticatedClient = new TestClient();
    const agentId = createdAgent.agent_id || createdAgent.id;

    await expect(unauthenticatedClient.getAgent(agentId))
      .rejects.toThrow();
  });

  test('should reject access to non-existent agent', async () => {
    await expect(client.getAgent('non-existent-agent-id'))
      .rejects.toThrow();
  });
});

describe('Agent - Update', () => {
  let client;
  let createdAgent;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    await client.signup(
      generateTestEmail('agentupdate'),
      'SecurePass123!',
      'Agent Update User'
    );
    await client.createCompany(generateTestCompanyName());
    createdAgent = await client.createAgent({ name: 'Original Name' });
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should update agent name', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    const newName = 'Updated Agent Name';
    
    const updated = await client.updateAgent(agentId, { name: newName });

    expect(updated.name).toBe(newName);
  });

  test('should update agent description', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    const newDescription = 'Updated description';
    
    const updated = await client.updateAgent(agentId, { description: newDescription });

    expect(updated.description).toBe(newDescription);
  });

  test('should update agent system prompt', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    const newPrompt = 'You are now an updated assistant.';
    
    const updated = await client.updateAgent(agentId, { system_prompt: newPrompt });

    expect(updated.system_prompt).toBe(newPrompt);
  });

  test('should update agent model', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    
    const updated = await client.updateAgent(agentId, { model: 'glm4:9b' });

    expect(updated.model).toBe('glm4:9b');
  });

  test('should reject update for non-existent agent', async () => {
    await expect(
      client.updateAgent('non-existent', { name: 'Test' })
    ).rejects.toThrow();
  });

  test('should reject update without authentication', async () => {
    const unauthenticatedClient = new TestClient();
    const agentId = createdAgent.agent_id || createdAgent.id;

    await expect(
      unauthenticatedClient.updateAgent(agentId, { name: 'Hacked' })
    ).rejects.toThrow();
  });
});

describe('Agent - Delete', () => {
  let client;
  let createdAgent;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    await client.signup(
      generateTestEmail('agentdelete'),
      'SecurePass123!',
      'Agent Delete User'
    );
    await client.createCompany(generateTestCompanyName());
    createdAgent = await client.createAgent({ name: generateTestAgentName() });
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should delete existing agent', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    
    await client.deleteAgent(agentId);

    // Verify agent no longer exists
    await expect(client.getAgent(agentId)).rejects.toThrow();
  });

  test('should not list deleted agent', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    await client.deleteAgent(agentId);

    const agents = await client.listAgents();
    const deletedAgent = agents.find(a => (a.agent_id || a.id) === agentId);
    
    expect(deletedAgent).toBeUndefined();
  });

  test('should reject delete without authentication', async () => {
    const unauthenticatedClient = new TestClient();
    const agentId = createdAgent.agent_id || createdAgent.id;

    await expect(unauthenticatedClient.deleteAgent(agentId))
      .rejects.toThrow();
  });

  test('should reject delete of non-existent agent', async () => {
    await expect(client.deleteAgent('non-existent'))
      .rejects.toThrow();
  });
});

describe('Agent - Tenant Isolation', () => {
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    await dbHelper.cleanTables();
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should not see agents from other tenants', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    // Setup tenant 1
    await client1.signup(generateTestEmail('isoa1'), 'Pass123!', 'User 1');
    await client1.createCompany(generateTestCompanyName());
    await client1.createAgent({ name: 'Tenant 1 Agent' });

    // Setup tenant 2
    await client2.signup(generateTestEmail('isoa2'), 'Pass123!', 'User 2');
    await client2.createCompany(generateTestCompanyName());
    await client2.createAgent({ name: 'Tenant 2 Agent' });

    // Each should only see their own agent
    const agents1 = await client1.listAgents();
    const agents2 = await client2.listAgents();

    expect(agents1.length).toBe(1);
    expect(agents1[0].name).toBe('Tenant 1 Agent');

    expect(agents2.length).toBe(1);
    expect(agents2[0].name).toBe('Tenant 2 Agent');
  });

  test('should not access other tenant agent by ID', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('isoacc1'), 'Pass123!', 'User 1');
    await client1.createCompany(generateTestCompanyName());
    const agent1 = await client1.createAgent({ name: 'Private Agent' });

    await client2.signup(generateTestEmail('isoacc2'), 'Pass123!', 'User 2');
    await client2.createCompany(generateTestCompanyName());

    // Tenant 2 should not access Tenant 1's agent
    const agentId = agent1.agent_id || agent1.id;
    await expect(client2.getAgent(agentId)).rejects.toThrow();
  });

  test('should not update other tenant agent', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('isoupd1'), 'Pass123!', 'User 1');
    await client1.createCompany(generateTestCompanyName());
    const agent1 = await client1.createAgent({ name: 'Original Name' });

    await client2.signup(generateTestEmail('isoupd2'), 'Pass123!', 'User 2');
    await client2.createCompany(generateTestCompanyName());

    // Tenant 2 should not update Tenant 1's agent
    const agentId = agent1.agent_id || agent1.id;
    await expect(
      client2.updateAgent(agentId, { name: 'Hacked Name' })
    ).rejects.toThrow();
  });

  test('should not delete other tenant agent', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('isodel1'), 'Pass123!', 'User 1');
    await client1.createCompany(generateTestCompanyName());
    const agent1 = await client1.createAgent({ name: 'Protected Agent' });

    await client2.signup(generateTestEmail('isodel2'), 'Pass123!', 'User 2');
    await client2.createCompany(generateTestCompanyName());

    // Tenant 2 should not delete Tenant 1's agent
    const agentId = agent1.agent_id || agent1.id;
    await expect(client2.deleteAgent(agentId)).rejects.toThrow();

    // Verify agent still exists for tenant 1
    const agent = await client1.getAgent(agentId);
    expect(agent).toBeDefined();
  });
});

describe('Agent - Chat Integration', () => {
  let client;
  let createdAgent;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    await client.signup(
      generateTestEmail('agentchat'),
      'SecurePass123!',
      'Chat User'
    );
    await client.createCompany(generateTestCompanyName());
    createdAgent = await client.createAgent({ name: generateTestAgentName() });
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should send message to agent', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    
    const response = await client.chat(agentId, 'Hello, test message');

    expect(response).toBeDefined();
    // Response structure may vary - just verify it exists
    expect(response).toHaveProperty('message') || expect(response).toHaveProperty('response');
  });

  test('should get conversation history', async () => {
    const agentId = createdAgent.agent_id || createdAgent.id;
    
    // Send a message first
    await client.chat(agentId, 'Test message for history');

    // Get conversation
    const conversation = await client.getConversation(agentId);

    expect(conversation).toBeDefined();
    expect(conversation.agent_id || conversation.agentId).toBe(agentId);
  });

  test('should reject chat without authentication', async () => {
    const unauthenticatedClient = new TestClient();
    const agentId = createdAgent.agent_id || createdAgent.id;

    await expect(
      unauthenticatedClient.chat(agentId, 'Hello')
    ).rejects.toThrow();
  });

  test('should reject chat with non-existent agent', async () => {
    await expect(
      client.chat('non-existent', 'Hello')
    ).rejects.toThrow();
  });
});