# NewFire n8n Integration

n8n is the workflow orchestrator for NewFire. Operators use it to react to platform events (signup, tier upgrade, agent created) and to call NewFire agents from external triggers (calendar, email, forms).

## Event emission: NewFire to n8n

The backend emits signed JSON webhooks when lifecycle events happen. Each event has a dedicated env var that names the n8n webhook URL. If the env var is empty, the emission is skipped.

| Event | Env var | Payload |
|---|---|---|
| `user.signup` | `N8N_HOOK_USER_SIGNUP` | `{ user_id, email, name }` |
| `user.onboarded` | `N8N_HOOK_USER_ONBOARDED` | `{ user_id, company_id, agents }` |
| `subscription.upgraded` | `N8N_HOOK_SUBSCRIPTION_UPGRADED` | `{ user_id, from_tier, to_tier }` |
| `agent.created` | `N8N_HOOK_AGENT_CREATED` | `{ agent_id, company_id, name }` |

Each request carries these headers and body:
- `Content-Type: application/json`
- `X-Event-Type: <event-name>`
- `X-Signature: sha256=<hex>` is HMAC-SHA256 of the raw body with `N8N_HOOK_SECRET`
- Body shape: `{ "event": "<event-name>", "payload": { ... }, "emitted_at": "ISO8601" }`

The starter workflow `welcome-new-signup.json` shows the canonical pattern: webhook, then HMAC verify, then branch on event, then action.

## Agent invocation: n8n to NewFire

n8n workflows call NewFire agents through APISIX. Each Pro client has a per-consumer API key.

```
POST https://newfire.app/api/agents/{agent_id}/chat
Headers:
  X-API-Key: <client api key>
  Content-Type: application/json
Body:
  { "messages": [ { "role": "user", "content": "..." } ] }
```

Typical HTTP Request node configuration in n8n:
- Method: POST
- URL: `https://newfire.app/api/agents/{{ $env.NEWFIRE_AGENT_ID }}/chat`
- Authentication: Header Auth, header name `X-API-Key`, value `{{ $env.NEWFIRE_API_KEY }}`
- Body: `{ "messages": [{ "role": "user", "content": "{{ $json.input }}" }] }`

## Installing the starter workflow

1. Set up the env vars in backend `.env`:
   - `N8N_HOOK_SECRET` is the shared secret for HMAC (auto generated on first deploy)
   - `N8N_HOOK_USER_SIGNUP=https://<your n8n host>/webhook/newfire-user-signup`
2. Restart the backend.
3. In n8n, open Import and paste `welcome-new-signup.json`.
4. Activate the workflow. The webhook path must match the env var URL.
5. Make `N8N_HOOK_SECRET` available to the n8n instance (same value as the backend).
6. Test by signing up a new user on newfire.app and watching the execution log.

## Security

- HMAC signature verification is non optional. The starter workflow throws on invalid signatures.
- Rotate `N8N_HOOK_SECRET` via `openssl rand -hex 32` and update both sides simultaneously.
- Never expose raw n8n webhook URLs in client code because they carry action capability.
