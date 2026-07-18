# {{Service Name}}

## Overview

- **Service:** {{Service Name}}
- **Container:** {{Container Name}}
- **Image:** {{Image Name:Version}}
- **Status:** {{Status}}
- **Last Updated:** {{Date}}

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| {{Port}} | {{TCP/UDP}} | {{Purpose}} |

## Configuration

**Config File:** `{{Path to config file}}`  
**Environment:** `{{Key environment variables}}`

## Dependencies

- **Database:** {{Database service}}
- **Cache:** {{Cache service}}
- **Message Queue:** {{MQ service}}
- **Other:** {{Other dependencies}}

## Health Check

```bash
# Check service status
docker ps | grep {{container-name}}

# Check logs
docker logs {{container-name}} --tail 50

# Check health endpoint
curl http://localhost:{{port}}/health
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check logs: `docker logs {{container-name}}`
   - Check ports: `docker port {{container-name}}`
   - Check resources: `docker stats`

2. **Connection refused**
   - Verify container is running: `docker ps`
   - Check network: `docker network inspect app-net`
   - Verify service is listening: `netstat -tlnp | grep {{port}}`

3. **High resource usage**
   - Check limits: `docker inspect {{container-name}} --format '{{.HostConfig.MemoryLimit}}'`
   - Increase limits: `docker update --memory={{new-limit}} {{container-name}}`

## Documentation

- **Official Docs:** {{URL to official documentation}}
- **Internal Docs:** [[Related note]]
- **Configuration:** [[Service-Config]]

## Change History

| Date | Change | Reason |
|------|--------|--------|
| {{Date}} | {{Change}} | {{Reason}} |
