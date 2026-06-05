// Pricing tier definitions. Source of truth for limits and features.
// Referenced by server.js (public /tiers endpoint, enforcement) and by the SPA pricing page.

export const TIERS = {
  free: {
    id: 'free',
    name: 'Free',
    price_usd_monthly: 0,
    stripe_price_id: null, // no subscription
    agent_cap: 3,
    message_cap_monthly: 100,
    monthly_budget_usd: 2,
    allow_cloud_models: false,
    rag_chunk_cap: 50,
    workflow_builder: false,
    support: 'community',
    privacy_mode_available: false,
    tagline: 'Build your full team, try it out',
    features: [
      'Up to 3 agents',
      '100 messages per month',
      'Local models only',
      'RAG up to 50 chunks',
      'Community support',
    ],
    cta: 'Sign Up Free',
  },
  starter: {
    id: 'starter',
    name: 'Starter',
    price_usd_monthly: 29,
    stripe_price_id: process.env.STRIPE_PRICE_STARTER || null,
    agent_cap: 5,
    message_cap_monthly: 1000,
    monthly_budget_usd: 10,
    allow_cloud_models: true,
    rag_chunk_cap: 500,
    workflow_builder: false,
    support: 'email',
    privacy_mode_available: false,
    tagline: 'For solo founders',
    features: [
      'Up to 5 agents',
      '1,000 messages per month',
      'Cloud models included',
      'RAG up to 500 chunks',
      'Email support',
    ],
    cta: 'Start with Starter',
  },
  pro: {
    id: 'pro',
    name: 'Pro',
    price_usd_monthly: 99,
    stripe_price_id: process.env.STRIPE_PRICE_PRO || null,
    agent_cap: 15,
    message_cap_monthly: 10000,
    monthly_budget_usd: 50,
    allow_cloud_models: true,
    rag_chunk_cap: 5000,
    workflow_builder: true,
    support: 'priority',
    privacy_mode_available: false,
    tagline: 'For growing small businesses',
    features: [
      'Up to 15 agents',
      '10,000 messages per month',
      'All models including Kimi and Claude',
      'RAG up to 5,000 chunks',
      'n8n workflow builder access',
      'Priority support',
    ],
    cta: 'Upgrade to Pro',
    popular: true,
  },
  enterprise: {
    id: 'enterprise',
    name: 'Enterprise',
    price_usd_monthly: null, // custom
    stripe_price_id: null,
    agent_cap: null, // unlimited
    message_cap_monthly: null,
    monthly_budget_usd: null,
    allow_cloud_models: true,
    rag_chunk_cap: null,
    workflow_builder: true,
    support: 'dedicated',
    privacy_mode_available: true,
    tagline: 'For legal, healthcare, and regulated industries',
    features: [
      'Unlimited agents',
      'Unlimited messages',
      'Privacy mode (cloud-off available)',
      'Dedicated support',
      'SOC2 path, data residency',
      'Audit log, compliance reviews',
      'Custom integrations',
    ],
    cta: 'Contact Sales',
    contact_only: true,
  },
}

export function getTier(tierId) {
  return TIERS[tierId] || TIERS.free
}

export function listTiers() {
  return Object.values(TIERS)
}
