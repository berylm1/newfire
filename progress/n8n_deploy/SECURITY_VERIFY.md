# n8n Security Verification (run after each client deploy)

Tick every box before routing real client traffic.

## On Minisforum

- [ ] `ss -tlnp | grep 567` shows only `127.0.0.1:567X` lines, no `0.0.0.0` and no `*:567X`
- [ ] `ls -la /home/newwaveclaw/n8n/<client>/.env` shows `-rw-------` and owner `newwaveclaw`
- [ ] `docker inspect n8n-<client> --format '{{.HostConfig.RestartPolicy.Name}}'` returns `unless-stopped`
- [ ] `docker exec n8n-<client> printenv N8N_ENCRYPTION_KEY | wc -c` returns 65 (64 hex + newline)
- [ ] `sudo -u postgres psql -c "\du n8n_<client>"` shows no `SUPERUSER`, no `CREATEDB`, no `CREATEROLE`
- [ ] `sudo ufw status` shows 5678 through 5689 are NOT in the allow list
- [ ] `fail2ban-client status` still shows sshd jail active

## On APISIX

- [ ] `curl -s https://<client>.newfire.ai/rest/login` without key returns 401
- [ ] `curl -s -H "apikey: <wrong>" https://<client>.newfire.ai/rest/login` returns 401
- [ ] `curl -s -H "apikey: <right>" https://<client>.newfire.ai/rest/login` returns 200 (or n8n's login JSON)
- [ ] 61 back-to-back requests with the right key hit HTTP 429 at request 61 (limit-req proves out)
- [ ] `curl -s https://<client>.newfire.ai/` returns the n8n UI with CORS headers scoped to the same origin

## On Ziti

- [ ] `ziti edge list services` shows `n8n-admin-<client>`
- [ ] Policy bind+dial restricted to identity `newwaveclaw-laptop`, not `#all`
- [ ] Tunneling from laptop: `curl http://n8n-admin-<client>.ziti/healthz` returns 200
- [ ] Tunneling from a non-bound identity: same request fails with no route

## On n8n itself

- [ ] Owner account created with unique email + 16+ char password
- [ ] 2FA enrolled on owner account
- [ ] `Settings -> Users` shows no other users with Owner role
- [ ] `Settings -> Security -> Disable production main process webhook rejection` is OFF
- [ ] At least one test workflow calls Paperclip via HTTP Request node using a stored credential, not an inline key
- [ ] Credential secrets are encrypted at rest (verify by dumping `credentials` table; `data` column must be base64 ciphertext, not JSON)

## Backup proof

- [ ] `pg_dump n8n_<client>` written to `/mnt/backups/n8n/<client>/$(date +%F).sql.zst`
- [ ] restic snapshot of `/var/lib/docker/volumes/n8n_<client>_data` exists on DGX Spark
- [ ] Restore rehearsal: spin up `n8n-<client>-restore` on port 5699, seed from backup, confirm workflows load

## Logging + observability

- [ ] Loki shows `container=n8n-<client>` stream with recent lines
- [ ] Grafana `NewFire / n8n` dashboard has a row for this client
- [ ] Alert: error rate > 5% over 5 min pages `#newfire-oncall`

If any box stays unchecked, the client does not get the URL.
