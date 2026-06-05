import test from 'node:test'
import assert from 'node:assert/strict'

process.env.JWT_SECRET ||= 'test-secret-that-is-long-enough-for-jwt-32'
process.env.DB_PASSWORD ||= 'test-password'

global.fetch = async () => ({ ok: true, json: async () => ({}), text: async () => '' })

const db = await import('../src/db.js')
const auth = await import('../src/auth.js')
const tenant = await import('../src/tenant.js')
const orchestrator = await import('../src/orchestrator.js')

const originalConsoleLog = console.log

test.before(() => {
  console.log = () => {}
})

test.after(() => {
  console.log = originalConsoleLog
})

function createMemoryStore() {
  return {
    nextUserId: 1,
    nextCompanyId: 100,
    users: [],
    companies: [],
    agents: [],
  }
}

function makeFakeQuery(store) {
  return async function fakeQuery(sql, params = []) {
    const normalized = sql.replace(/\s+/g, ' ').trim()

    if (normalized.startsWith('SELECT id FROM users WHERE email')) {
      return { rows: store.users.filter((u) => u.email === params[0]).map((u) => ({ id: u.id })) }
    }

    if (normalized.startsWith('INSERT INTO users')) {
      const user = {
        id: store.nextUserId++,
        email: params[0],
        password_hash: params[1],
        name: params[2],
        role: 'user',
        onboarded: false,
        company_id: null,
      }
      store.users.push(user)
      return { rows: [{ id: user.id, email: user.email, name: user.name, role: user.role, onboarded: user.onboarded }] }
    }

    if (normalized.startsWith('SELECT * FROM users WHERE email')) {
      return { rows: store.users.filter((u) => u.email === params[0]) }
    }

    if (normalized.startsWith('SELECT id, role, company_id FROM users WHERE id')) {
      const user = store.users.find((u) => u.id === params[0])
      return { rows: user ? [{ id: user.id, role: user.role, company_id: user.company_id }] : [] }
    }

    if (normalized.startsWith('SELECT id, name FROM companies WHERE user_id')) {
      return { rows: store.companies.filter((c) => c.user_id === params[0]).slice(0, 1).map((c) => ({ id: c.id, name: c.name })) }
    }

    if (normalized.startsWith('INSERT INTO companies')) {
      const company = {
        id: store.nextCompanyId++,
        user_id: params[0],
        name: params[1],
        description: params[2],
        tier: params[3],
        monthly_budget_usd: params[4],
        allow_cloud_models: params[5],
        qdrant_collection: null,
      }
      store.companies.push(company)
      return { rows: [{ id: company.id }] }
    }

    if (normalized.startsWith('UPDATE companies SET qdrant_collection')) {
      const company = store.companies.find((c) => c.id === params[1])
      if (company) company.qdrant_collection = params[0]
      return { rows: [] }
    }

    if (normalized.startsWith('UPDATE users SET company_id')) {
      const user = store.users.find((u) => u.id === params[1] && u.company_id == null)
      if (user) user.company_id = params[0]
      return { rows: [] }
    }

    if (normalized.startsWith('INSERT INTO agents')) {
      const agent = {
        id: store.agents.length + 1,
        company_id: params[0],
        agent_id: params[1],
        name: params[2],
        role: params[3],
        description: params[4],
        system_prompt: params[5],
        model: params[6],
        provider: params[7],
        icon: params[8],
        color: params[9],
        created_at: new Date().toISOString(),
      }
      store.agents.push(agent)
      return { rows: [agent] }
    }

    if (normalized.startsWith('UPDATE users SET onboarded = TRUE')) {
      const user = store.users.find((u) => u.id === params[0])
      if (user) {
        user.onboarded = true
        user.role = params[1]
      }
      return { rows: [] }
    }

    if (normalized.startsWith('UPDATE companies SET paperclip_status')) {
      return { rows: [] }
    }

    if (normalized.startsWith('INSERT INTO tenant_provisioning_queue')) {
      return { rows: [] }
    }

    if (normalized.startsWith('SELECT a.* FROM agents a JOIN companies c ON a.company_id = c.id WHERE c.user_id')) {
      const companies = store.companies.filter((c) => c.user_id === params[0]).map((c) => c.id)
      return { rows: store.agents.filter((a) => companies.includes(a.company_id)) }
    }

    if (normalized.startsWith('SELECT a.*, c.qdrant_collection FROM agents a JOIN companies c ON a.company_id = c.id WHERE a.company_id')) {
      const agent = store.agents.find((a) => a.company_id === params[0] && a.agent_id === params[1])
      if (!agent) return { rows: [] }
      const company = store.companies.find((c) => c.id === agent.company_id)
      return { rows: [{ ...agent, qdrant_collection: company?.qdrant_collection || null }] }
    }

    throw new Error(`Unhandled fake query: ${normalized}`)
  }
}

async function seedTwoTenants() {
  const store = createMemoryStore()
  db.setQueryImplementation(makeFakeQuery(store))

  const alpha = await auth.signup('owner-alpha@example.com', 'correct horse battery staple', 'Owner Alpha')
  const beta = await auth.signup('owner-beta@example.com', 'correct horse battery staple', 'Owner Beta')

  const alphaCompany = await orchestrator.createCompanyForUser(alpha.user.id, 'Alpha Co', 'Alpha business', [
    { name: 'Sales Agent', role: 'sales', description: 'Handles leads' },
  ])
  const betaCompany = await orchestrator.createCompanyForUser(beta.user.id, 'Beta Co', 'Beta business', [
    { name: 'Support Agent', role: 'support', description: 'Handles support' },
  ])

  return { store, alpha, beta, alphaCompany, betaCompany }
}

test.afterEach(() => {
  db.resetQueryImplementation()
})

test('signup and login produce a reusable authenticated user token', async () => {
  const store = createMemoryStore()
  db.setQueryImplementation(makeFakeQuery(store))

  const signup = await auth.signup('User@Example.com', 'correct horse battery staple', 'Test User')
  assert.equal(signup.user.email, 'user@example.com')
  assert.ok(signup.token)

  const login = await auth.login('user@example.com', 'correct horse battery staple')
  assert.equal(login.user.id, signup.user.id)
  assert.ok(login.token)
})

test('company creation assigns tenant context and only returns that tenant agents', async () => {
  const { alpha, beta, alphaCompany, betaCompany } = await seedTwoTenants()

  assert.notEqual(alphaCompany.companyId, betaCompany.companyId)
  assert.equal((await tenant.loadTenant(alpha.user.id)).companyId, alphaCompany.companyId)
  assert.equal((await tenant.loadTenant(beta.user.id)).companyId, betaCompany.companyId)

  const alphaAgents = await orchestrator.getUserAgents(alpha.user.id)
  const betaAgents = await orchestrator.getUserAgents(beta.user.id)
  assert.deepEqual(alphaAgents.map((a) => a.agent_id), ['sales-agent'])
  assert.deepEqual(betaAgents.map((a) => a.agent_id), ['support-agent'])
})

test('tenant agent lookup denies cross-tenant agent access', async () => {
  const { alphaCompany, betaCompany } = await seedTwoTenants()

  const ownAgent = await orchestrator.getTenantAgent(alphaCompany.companyId, 'sales-agent')
  assert.equal(ownAgent.agent_id, 'sales-agent')

  const crossTenantAgent = await orchestrator.getTenantAgent(betaCompany.companyId, 'sales-agent')
  assert.equal(crossTenantAgent, null)
})
