# Execution sequence: deploy n8n-sherifah

Run every step from your Mac terminal in this order. I cannot reach the
homelab myself, so each command is yours to paste.

## Step 0: save secrets (do this first)

Copy these three values into 1Password under `NewFire / n8n / sherifah`:

- n8n encryption key: `373f7d2f267bad210514e5d8772ddddcc2c800874153fed1a383c4eaeb52a886`
- postgres password:  `QAXQA1IvGi0ecNS7kLLZcJEc`
- apisix consumer key: `acf722f183f0b23785f79bd63ef635749d42f28b11c71cb4`

After saving, clear your terminal scrollback so the keys do not linger.

## Step 1: provision Postgres role and database on Minisforum

```
cd /Users/oluwajobamalomo/Desktop/AI_Homelab_Setup/progress/n8n_deploy
sed "s/REPLACE_DB_PASSWORD/QAXQA1IvGi0ecNS7kLLZcJEc/" postgres_setup.sql > /tmp/postgres_setup_filled.sql
scp /tmp/postgres_setup_filled.sql newwaveclaw@america:/tmp/postgres_setup.sql
ssh newwaveclaw@america 'sudo -u postgres psql -f /tmp/postgres_setup.sql && shred -u /tmp/postgres_setup.sql'
rm /tmp/postgres_setup_filled.sql
```

Verify: `ssh newwaveclaw@america 'sudo -u postgres psql -tAc "\\du n8n_sherifah"'`
should print `n8n_sherifah|{}|{}` or similar, with no SUPERUSER attributes.

## Step 2: dry run the deploy

```
cd /Users/oluwajobamalomo/Desktop/AI_Homelab_Setup/progress/n8n_deploy
./deploy.sh sherifah --dry-run
```

Read every line. If any path or command looks wrong, stop and tell me.

## Step 3: real deploy

```
./deploy.sh sherifah
```

Expected final lines:
```
==> [5/6] wait for healthy
healthy
==> [6/6] verify loopback + no public binding
{"status":"ok"}
done. next: apply APISIX route + Caddy vhost + Ziti service. see PLAN.md.
```

If it halts at step 5, the container is not healthy. Grab logs:
`ssh newwaveclaw@america 'docker logs --tail 100 n8n-sherifah'` and paste back.

## Step 4: register APISIX route and consumer

The APISIX admin API lives on `127.0.0.1:9180` on Minisforum. You already
have `$APISIX_ADMIN_KEY` set on that host (it is the APISIX control-plane
key, not the per-client one we generated).

```
scp apisix_route_sherifah.json apisix_consumer_sherifah.json newwaveclaw@america:/tmp/
ssh newwaveclaw@america 'source /etc/apisix/admin.env && \
  curl -sS -X PUT http://127.0.0.1:9180/apisix/admin/routes/n8n-sherifah \
    -H "X-API-KEY: $APISIX_ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d @/tmp/apisix_route_sherifah.json | python3 -m json.tool | head -20 && \
  curl -sS -X PUT http://127.0.0.1:9180/apisix/admin/consumers/sherifah \
    -H "X-API-KEY: $APISIX_ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d @/tmp/apisix_consumer_sherifah.json | python3 -m json.tool | head -20 && \
  shred -u /tmp/apisix_route_sherifah.json /tmp/apisix_consumer_sherifah.json'
```

Both responses should show `"createdIndex"` and no `error_msg`.

## Step 5: smoke test the gateway

```
ssh newwaveclaw@america 'curl -i -H "Host: sherifah.newfire.ai" http://127.0.0.1:9080/'
```
Expect `401 Unauthorized` with `error_msg":"Missing API key`.

```
ssh newwaveclaw@america 'curl -i -H "Host: sherifah.newfire.ai" -H "apikey: acf722f183f0b23785f79bd63ef635749d42f28b11c71cb4" http://127.0.0.1:9080/'
```
Expect `200 OK` with n8n HTML (`<!doctype html>`).

## Step 6: (optional for today) Caddy vhost + Ziti admin service

Skip if DNS for `sherifah.newfire.ai` is not cut over yet. The loopback
smoke test above already proves the pipeline from APISIX to n8n works.

## Step 7: run both test batteries together

Once step 5 is green:

```
# terminal A: Qdrant RAG on DGX
scp /Users/oluwajobamalomo/Desktop/AI_Homelab_Setup/progress/qdrant_test/test_qdrant_rag.sh newwave-dgx@ghana:~/
ssh newwave-dgx@ghana 'bash ~/test_qdrant_rag.sh' 2>&1 | tee /tmp/qdrant_out.log

# terminal B: MCP + Paperclip on Minisforum
scp /Users/oluwajobamalomo/Desktop/AI_Homelab_Setup/progress/qdrant_test/test_mcp_tool.sh newwaveclaw@america:~/
ssh newwaveclaw@america 'bash ~/test_mcp_tool.sh' 2>&1 | tee /tmp/mcp_out.log
```

Paste both logs back and I will mark the gap-map items verified.

## If you want to stop and roll back

On Minisforum:
```
ssh newwaveclaw@america 'cd /home/newwaveclaw/n8n/sherifah && docker compose down -v'
ssh newwaveclaw@america 'source /etc/apisix/admin.env && \
  curl -sS -X DELETE http://127.0.0.1:9180/apisix/admin/routes/n8n-sherifah -H "X-API-KEY: $APISIX_ADMIN_KEY" && \
  curl -sS -X DELETE http://127.0.0.1:9180/apisix/admin/consumers/sherifah -H "X-API-KEY: $APISIX_ADMIN_KEY"'
ssh newwaveclaw@america 'sudo -u postgres psql -c "DROP DATABASE n8n_sherifah; DROP ROLE n8n_sherifah;"'
```

That removes the container, volume, APISIX config, and Postgres state with
no residue.
