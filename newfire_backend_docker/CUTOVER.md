# newfire-backend Containerization Cutover

Target: replace systemd-managed host process `newfire-backend.service` with Dockerized container at the same bind `127.0.0.1:3200`. Zero data loss. Rollback is one systemd start away.

## Safety posture

- DB is a separate container (`newfire-db`). Backend is stateless, so the switch is purely runtime.
- Keep systemd unit FILE intact (do not delete). We only stop + disable the service, not remove it.
- Stage on port 3201 first to prove health, then flip 3200.
- Full rollback: `docker compose down` and `systemctl start newfire-backend` restores previous state.

## One time prep

1. SSH to Minisforum as newwaveclaw.
2. Create the Docker directory for the compose + env:
   ```
   mkdir -p /home/newwaveclaw/newfire-backend-docker
   ```
3. SCP these files from Mac:
   ```
   scp Dockerfile .dockerignore docker-compose.yml .env.template \
     newwaveclaw@america:/home/newwaveclaw/newfire-backend-docker/
   ```
4. Copy Dockerfile + .dockerignore INTO the backend source tree so the build context is clean:
   ```
   ssh newwaveclaw@america \
     'cp /home/newwaveclaw/newfire-backend-docker/Dockerfile /home/newwaveclaw/newfire-backend/Dockerfile; \
      cp /home/newwaveclaw/newfire-backend-docker/.dockerignore /home/newwaveclaw/newfire-backend/.dockerignore'
   ```
5. Fill .env with real values. Pull from systemd unit:
   ```
   ssh newwaveclaw@america 'sudo systemctl cat newfire-backend.service | grep Environment'
   ```
   Copy DB_PASSWORD and OPENROUTER_KEY into `/home/newwaveclaw/newfire-backend-docker/.env`, chmod 600.

## Staged test on port 3201

6. Build image:
   ```
   ssh newwaveclaw@america 'cd /home/newwaveclaw/newfire-backend-docker && docker compose build'
   ```
7. Start on alt port:
   ```
   ssh newwaveclaw@america 'cd /home/newwaveclaw/newfire-backend-docker && HOST_PORT=3201 docker compose up -d'
   ```
8. Wait and verify health:
   ```
   ssh newwaveclaw@america 'sleep 15 && docker inspect -f "{{.State.Health.Status}}" newfire-backend && curl -fsS http://127.0.0.1:3201/health'
   ```
   Expect `healthy` and `{"status":"ok","service":"newfire-backend","version":"1.0.0"}`.
9. Verify DB connectivity (should return user row count):
   ```
   ssh newwaveclaw@america 'curl -fsS http://127.0.0.1:3201/health'
   ```
   (Note: /health does not touch DB in current code. If in doubt, try /auth/me with an expired token: expect 401 not 500, which means auth middleware + JWT decode worked, meaning Node is running.)

## Cutover

10. Stop systemd service (existing host process keeps running for 5 sec, then stops cleanly):
    ```
    ssh newwaveclaw@america 'sudo systemctl stop newfire-backend'
    ```
11. Immediately restart container on production port:
    ```
    ssh newwaveclaw@america 'cd /home/newwaveclaw/newfire-backend-docker && docker compose down && HOST_PORT=3200 docker compose up -d'
    ```
12. Verify end-to-end:
    ```
    curl -fsS https://newfire.app/backend/health
    ```
    Expect `{"status":"ok","service":"newfire-backend","version":"1.0.0"}`.

## Hardening after cutover

13. Disable systemd service so it does not race to rebind port 3200 on reboot:
    ```
    ssh newwaveclaw@america 'sudo systemctl disable newfire-backend'
    ```
    Do NOT delete the unit file. Keep as rollback.

14. Add docker-compose unit to systemd for autostart on reboot:
    ```
    sudo tee /etc/systemd/system/newfire-backend-compose.service > /dev/null <<EOF
    [Unit]
    Description=NewFire backend (Docker Compose)
    After=docker.service network-online.target
    Requires=docker.service

    [Service]
    Type=oneshot
    RemainAfterExit=yes
    WorkingDirectory=/home/newwaveclaw/newfire-backend-docker
    ExecStart=/usr/bin/docker compose up -d
    ExecStop=/usr/bin/docker compose down

    [Install]
    WantedBy=multi-user.target
    EOF
    sudo systemctl daemon-reload
    sudo systemctl enable newfire-backend-compose
    ```

## Rollback (if cutover fails)

```
ssh newwaveclaw@america 'cd /home/newwaveclaw/newfire-backend-docker && docker compose down; sudo systemctl start newfire-backend'
curl -fsS https://newfire.app/backend/health
```

## Observability

After cutover, logs live in `docker logs newfire-backend` instead of `journalctl -u newfire-backend`. Consider shipping to Loki later.

## Open follow-ups (not tonight)

- Sync source `nginx.conf` on Mac (`~/newfire-app/nginx.conf`) with the actual container's live config, because they drift (Mac source has `/api/` only; live container has `/backend/`, `/admin/consumers`, and `/api/`). Not urgent for tonight.
- Add a per-request log line that includes user_id for audit (useful for Funmi's future privacy posture).
- Write an integration test that signs up a user, creates a company, and chats, so future cutovers prove product works.
