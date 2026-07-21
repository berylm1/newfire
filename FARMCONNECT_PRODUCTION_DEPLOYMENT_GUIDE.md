# FarmConnect Platform — Production Middleware & Services Deployment Guide

> **Complete Dockerization guide for deploying all 14 middleware components + 40+ polyglot microservices in an external production environment.**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Network Architecture](#3-network-architecture)
4. [Middleware Components (14)](#4-middleware-components)
   - 4.1 PostgreSQL + PostGIS (Database)
   - 4.2 PgBouncer (Connection Pooling)
   - 4.3 Redis (Cache & Sessions)
   - 4.4 Apache Kafka (Event Streaming)
   - 4.5 Fluvio (Real-Time Streaming)
   - 4.6 Keycloak (Identity & Auth)
   - 4.7 Permify (Authorization / RBAC)
   - 4.8 OpenSearch + Dashboards (Search & Analytics)
   - 4.9 Apache APISIX (API Gateway)
   - 4.10 OpenAppSec (WAF)
   - 4.11 TigerBeetle (Financial Ledger)
   - 4.12 Temporal (Workflow Orchestration)
   - 4.13 Dapr (Distributed Application Runtime)
   - 4.14 Mojaloop Simulator (Payment Interoperability)
5. [Observability Stack](#5-observability-stack)
   - 5.1 Prometheus
   - 5.2 Grafana
   - 5.3 Jaeger (Distributed Tracing)
   - 5.4 Loki + Promtail (Log Aggregation)
   - 5.5 HashiCorp Vault (Secrets Management)
6. [Application Services](#6-application-services)
   - 6.1 Main API (TypeScript/Node.js)
   - 6.2 Go Microservices (17 services)
   - 6.3 Rust Microservices (13 services)
   - 6.4 Python Microservices (23 services)
7. [Docker Compose — Full Production Stack](#7-docker-compose-full-production-stack)
8. [Startup Order & Dependencies](#8-startup-order--dependencies)
9. [Volume Management & Backups](#9-volume-management--backups)
10. [Environment Variables Reference](#10-environment-variables-reference)
11. [Security Hardening Checklist](#11-security-hardening-checklist)
12. [Scaling Guide](#12-scaling-guide)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL CLIENTS                            │
│              (Mobile PWA, Web Dashboard, USSD/SMS)                 │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ HTTPS (443)
┌─────────────────────▼───────────────────────────────────────────────┐
│                   APISIX API Gateway (:9080/:9443)                  │
│          Rate limiting · Auth · WAF · Load balancing                │
└──────┬─────────────────────────────────┬────────────────────────────┘
       │                                 │
┌──────▼──────────┐            ┌─────────▼──────────────────────────┐
│  OpenAppSec WAF │            │     Main API (Node.js :3000)       │
│    (:8085)      │            │  91 tRPC routers · JWT · Middleware │
└─────────────────┘            └──────┬────────────┬────────────────┘
                                      │            │
           ┌──────────────────────────┤            ├──────────────────┐
           │                          │            │                  │
    ┌──────▼──────┐  ┌───────────────▼──┐  ┌─────▼──────┐  ┌───────▼────────┐
    │ Go Services │  │  Rust Services   │  │ Python Svc │  │   Middleware    │
    │  (17 svcs)  │  │   (13 svcs)      │  │ (23 svcs)  │  │   (14 systems) │
    │ :8097-8120  │  │  :8099,:8104-8122 │  │:8001-8118  │  │                │
    └──────┬──────┘  └────────┬─────────┘  └─────┬──────┘  └────────┬───────┘
           │                  │                   │                  │
    ┌──────▼──────────────────▼───────────────────▼──────────────────▼──────┐
    │                       DATA & MESSAGING LAYER                          │
    │  PostgreSQL · Redis · Kafka · TigerBeetle · OpenSearch · Temporal     │
    └──────────────────────────────────────────────────────────────────────-─┘
```

**Total Services:** 54+ containers in production  
**Languages:** TypeScript, Go, Rust, Python  
**Middleware Systems:** 14 core + 5 observability  

---

## 2. Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker Engine | 24.0+ | 25.0+ |
| Docker Compose | v2.20+ | v2.27+ |
| RAM | 16 GB | 32 GB |
| CPU | 8 cores | 16 cores |
| Disk (SSD) | 100 GB | 250 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

```bash
# Install Docker + Compose on Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify
docker --version       # 25.x+
docker compose version # v2.27+
```

---

## 3. Network Architecture

Create an isolated Docker network for all services:

```bash
docker network create --driver bridge farmconnect-network
```

**Internal port assignments:**

| Port Range | Assignment |
|------------|-----------|
| 3000-3001 | Main API (HTTP + WebSocket) |
| 3476-3478 | Permify (HTTP + gRPC) |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 6432 | PgBouncer |
| 7233 | Temporal |
| 8001 | ML Service |
| 8080 | Keycloak |
| 8085 | OpenAppSec WAF |
| 8097-8122 | Polyglot microservices |
| 8200 | Vault |
| 8233 | Temporal UI |
| 8444 | Mojaloop |
| 9003 | Fluvio |
| 9080/9443 | APISIX (HTTP/HTTPS) |
| 9090 | Prometheus |
| 9092-9093 | Kafka (internal/external) |
| 9200 | OpenSearch |
| 16686 | Jaeger UI |
| 50005 | Dapr Placement |

---

## 4. Middleware Components

### 4.1 PostgreSQL + PostGIS (Primary Database)

**Purpose:** Primary relational database with geospatial extensions for farm location data, user records, transactions, and 249+ tables.

**Image:** `postgis/postgis:16-3.4-alpine`

```yaml
# docker-compose.prod.yml — PostgreSQL
postgres:
  image: postgis/postgis:16-3.4-alpine
  container_name: farmer-postgres
  restart: unless-stopped
  ports:
    - "5432:5432"
  environment:
    POSTGRES_DB: farmer_data
    POSTGRES_USER: ${DB_USER:-farmer_user}
    POSTGRES_PASSWORD: ${DB_PASSWORD}        # REQUIRED — set in .env
    POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
    PGDATA: /var/lib/postgresql/data/pgdata
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./drizzle/migrations:/docker-entrypoint-initdb.d:ro
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-farmer_user}"]
    interval: 10s
    timeout: 3s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "2.0"
      reservations:
        memory: 512M
  networks:
    - farmconnect-network
```

**Production hardening:**
```bash
# postgresql.conf tuning (mount via volume)
shared_buffers = 512MB
effective_cache_size = 1536MB
work_mem = 16MB
maintenance_work_mem = 128MB
max_connections = 200
wal_level = replica
max_wal_senders = 3
archive_mode = on
```

**Seed the database:**
```bash
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed.sql
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed-extended.sql
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed-remaining.sql
```

---

### 4.2 PgBouncer (Connection Pooling)

**Purpose:** Connection pooler sitting between the app and PostgreSQL. Reduces connection overhead from 200+ service connections to a controlled pool.

**Image:** `bitnami/pgbouncer:1.22.0`

```yaml
pgbouncer:
  image: bitnami/pgbouncer:1.22.0
  container_name: farmer-pgbouncer
  restart: unless-stopped
  ports:
    - "6432:6432"
  environment:
    PGBOUNCER_DATABASE: farmer_data
    PGBOUNCER_PORT: "6432"
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: "200"
    PGBOUNCER_DEFAULT_POOL_SIZE: "25"
    PGBOUNCER_MIN_POOL_SIZE: "5"
    POSTGRESQL_HOST: postgres
    POSTGRESQL_PORT: "5432"
    POSTGRESQL_USERNAME: ${DB_USER:-farmer_user}
    POSTGRESQL_PASSWORD: ${DB_PASSWORD}
    POSTGRESQL_DATABASE: farmer_data
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "pg_isready", "-h", "localhost", "-p", "6432"]
    interval: 10s
    timeout: 3s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 256M
        cpus: "0.5"
  networks:
    - farmconnect-network
```

**Connection string for app services:**
```
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@pgbouncer:6432/farmer_data
```

---

### 4.3 Redis (Cache, Sessions & Pub/Sub)

**Purpose:** In-memory cache for API responses, session store, rate limiting counters, and real-time pub/sub for WebSocket events.

**Image:** `redis:7-alpine`

```yaml
redis:
  image: redis:7-alpine
  container_name: farmer-redis
  restart: unless-stopped
  ports:
    - "6379:6379"
  command: >
    redis-server
    --appendonly yes
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --requirepass ${REDIS_PASSWORD}
    --save 60 1000
    --save 300 100
  volumes:
    - redis-data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 768M
        cpus: "1.0"
  networks:
    - farmconnect-network
```

---

### 4.4 Apache Kafka (Event Streaming)

**Purpose:** Distributed event streaming for asynchronous communication between services — price updates, transaction events, IoT telemetry, audit logs. Uses KRaft mode (no Zookeeper).

**Image:** `bitnami/kafka:3.7`

```yaml
kafka:
  image: bitnami/kafka:3.7
  container_name: farmer-kafka
  restart: unless-stopped
  ports:
    - "9092:9092"
    - "9093:9093"
  environment:
    KAFKA_CFG_NODE_ID: 0
    KAFKA_CFG_PROCESS_ROLES: controller,broker
    KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: 0@kafka:9094
    KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9094,EXTERNAL://:9093
    KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,EXTERNAL://${EXTERNAL_HOST:-localhost}:9093
    KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT
    KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
    KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE: "true"
    KAFKA_CFG_NUM_PARTITIONS: 4
    KAFKA_CFG_DEFAULT_REPLICATION_FACTOR: 1
    KAFKA_CFG_LOG_RETENTION_HOURS: 168  # 7 days
    KAFKA_CFG_LOG_RETENTION_BYTES: 1073741824  # 1GB per partition
  volumes:
    - kafka-data:/bitnami/kafka
  healthcheck:
    test: ["CMD-SHELL", "kafka-broker-api-versions.sh --bootstrap-server localhost:9092 || exit 1"]
    interval: 15s
    timeout: 10s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "2.0"
  networks:
    - farmconnect-network
```

**Key topics (auto-created):**
```
farmer.events, price.updates, iot.telemetry, payment.transactions,
chama.contribution, chama.loan.requested, federated.participant.joined,
federated.update.submitted, export.shipment.created, carbon.project.updated
```

---

### 4.5 Fluvio (Real-Time Streaming)

**Purpose:** Low-latency event streaming for real-time price feeds, IoT sensor data, and delivery tracking updates. Complements Kafka for sub-second streaming needs.

**Image:** `infinyon/fluvio:latest`

```yaml
fluvio:
  image: infinyon/fluvio:latest
  container_name: farmer-fluvio
  restart: unless-stopped
  ports:
    - "9003:9003"
  environment:
    FLUVIO_NODE_BIND_ADDR: 0.0.0.0:9003
  volumes:
    - fluvio-data:/var/lib/fluvio
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:9003/ || exit 1"]
    interval: 15s
    timeout: 5s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "1.0"
  networks:
    - farmconnect-network
```

---

### 4.6 Keycloak (Identity & Authentication)

**Purpose:** Enterprise identity management — SSO, OAuth 2.0, OpenID Connect, social login, user federation. Manages farmer/admin/agent roles.

**Image:** `quay.io/keycloak/keycloak:24.0`

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:24.0
  container_name: farmer-keycloak
  restart: unless-stopped
  ports:
    - "8080:8080"
  environment:
    KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USERNAME:-admin}
    KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}  # REQUIRED
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
    KC_DB_USERNAME: ${DB_USER:-farmer_user}
    KC_DB_PASSWORD: ${DB_PASSWORD}
    KC_HEALTH_ENABLED: "true"
    KC_METRICS_ENABLED: "true"
    KC_HOSTNAME: ${KEYCLOAK_HOSTNAME:-auth.farmconnect.app}
    KC_PROXY: edge
  command: start --optimized
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "exec 3<>/dev/tcp/localhost/8080"]
    interval: 15s
    timeout: 5s
    retries: 10
    start_period: 60s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "1.0"
  networks:
    - farmconnect-network
```

**Post-deploy setup:**
```bash
# Create the farmconnect realm via Keycloak admin API
docker exec farmer-keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password $KEYCLOAK_ADMIN_PASSWORD

docker exec farmer-keycloak /opt/keycloak/bin/kcadm.sh create realms \
  -s realm=farmer-data-collection -s enabled=true

docker exec farmer-keycloak /opt/keycloak/bin/kcadm.sh create clients \
  -r farmer-data-collection -s clientId=farmconnect-app -s enabled=true \
  -s publicClient=true -s 'redirectUris=["https://farmconnect.app/*"]'
```

> **Production note:** Use `start --optimized` (not `start-dev`) and set `KC_HOSTNAME` to your real domain. Create a separate `keycloak` database in PostgreSQL.

---

### 4.7 Permify (Authorization / RBAC)

**Purpose:** Fine-grained relationship-based access control (ReBAC). Manages roles (farmer, admin, agent, buyer, cooperative_leader) and resource permissions.

**Image:** `ghcr.io/permify/permify:latest`

```yaml
permify:
  image: ghcr.io/permify/permify:latest
  container_name: farmer-permify
  restart: unless-stopped
  ports:
    - "3476:3476"   # HTTP API
    - "3478:3478"   # gRPC
  command: serve
  environment:
    PERMIFY_DATABASE_ENGINE: postgres
    PERMIFY_DATABASE_URI: "postgres://${DB_USER}:${DB_PASSWORD}@postgres:5432/permify"
    PERMIFY_LOG_LEVEL: info
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "wget --quiet --tries=1 --spider http://localhost:3476/healthz || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "0.5"
  networks:
    - farmconnect-network
```

> **Setup:** Create a separate `permify` database in PostgreSQL: `CREATE DATABASE permify;`

---

### 4.8 OpenSearch + Dashboards (Search & Analytics)

**Purpose:** Full-text search for marketplace products, farmer profiles, commodity listings. Analytics dashboards for platform operations.

**Image:** `opensearchproject/opensearch:2.12.0`

```yaml
opensearch:
  image: opensearchproject/opensearch:2.12.0
  container_name: farmer-opensearch
  restart: unless-stopped
  ports:
    - "9200:9200"
    - "9600:9600"
  environment:
    discovery.type: single-node
    OPENSEARCH_INITIAL_ADMIN_PASSWORD: ${OPENSEARCH_PASSWORD}
    OPENSEARCH_JAVA_OPTS: "-Xms1g -Xmx1g"
    plugins.security.disabled: "false"   # Enable in production
  volumes:
    - opensearch-data:/usr/share/opensearch/data
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health || exit 1"]
    interval: 15s
    timeout: 5s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "2.0"
  networks:
    - farmconnect-network

opensearch-dashboards:
  image: opensearchproject/opensearch-dashboards:2.12.0
  container_name: farmer-opensearch-dashboards
  restart: unless-stopped
  ports:
    - "5601:5601"
  environment:
    OPENSEARCH_HOSTS: '["http://opensearch:9200"]'
  depends_on:
    opensearch:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:5601/api/status || exit 1"]
    interval: 15s
    timeout: 5s
    retries: 5
    start_period: 30s
  deploy:
    resources:
      limits:
        memory: 1G
  networks:
    - farmconnect-network
```

> **Production:** Set `OPENSEARCH_JAVA_OPTS: "-Xms2g -Xmx2g"` and enable security plugin with real certificates.

---

### 4.9 Apache APISIX (API Gateway)

**Purpose:** Edge API gateway — rate limiting, authentication, load balancing, request transformation, and traffic routing to backend services.

**Image:** `apache/apisix:3.7.0-debian`

```yaml
apisix:
  image: apache/apisix:3.7.0-debian
  container_name: farmer-apisix
  restart: unless-stopped
  ports:
    - "9080:9080"    # HTTP proxy
    - "9443:9443"    # HTTPS proxy
    - "9180:9180"    # Admin API
  volumes:
    - ./apisix/config.yaml:/usr/local/apisix/conf/config.yaml:ro
    - ./apisix/apisix.yaml:/usr/local/apisix/conf/apisix.yaml:ro
  environment:
    APISIX_STAND_ALONE: "true"
  depends_on:
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9080/health"]
    interval: 10s
    timeout: 3s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "1.0"
  networks:
    - farmconnect-network
```

**Minimal `apisix/config.yaml`:**
```yaml
apisix:
  node_listen: 9080
  enable_admin: true
  admin_key:
    - name: admin
      key: ${APISIX_ADMIN_KEY}
      role: admin
nginx_config:
  http:
    lua_shared_dict:
      limit-req-store: 50m
      limit-count-store: 50m
```

---

### 4.10 OpenAppSec (Web Application Firewall)

**Purpose:** AI-driven web application firewall — blocks SQL injection, XSS, CSRF, and zero-day attacks. Operates in learning mode initially, then enforcement mode.

**Image:** `ghcr.io/openappsec/smartsync:latest`

```yaml
openappsec:
  image: ghcr.io/openappsec/smartsync:latest
  container_name: farmer-openappsec
  restart: unless-stopped
  ports:
    - "8085:8080"
  environment:
    LEARNING_MODE: "false"   # Set to "true" initially, "false" for enforcement
    LOG_LEVEL: info
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "1.0"
  networks:
    - farmconnect-network
```

---

### 4.11 TigerBeetle (Financial Ledger)

**Purpose:** High-performance double-entry accounting ledger for financial transactions — mobile money, loan disbursements, escrow, chama savings, carbon credit trading.

**Image:** `ghcr.io/tigerbeetle/tigerbeetle:0.16.6`

```yaml
tigerbeetle:
  image: ghcr.io/tigerbeetle/tigerbeetle:0.16.6
  container_name: farmer-tigerbeetle
  restart: unless-stopped
  ports:
    - "3000:3000"
  command: start --addresses=0.0.0.0:3000 /data/0_0.tigerbeetle
  volumes:
    - tigerbeetle-data:/data
  healthcheck:
    test: ["CMD-SHELL", "nc -z localhost 3000 || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "1.0"
  networks:
    - farmconnect-network
```

**Initialize the data file (first run only):**
```bash
docker run --rm -v tigerbeetle-data:/data \
  ghcr.io/tigerbeetle/tigerbeetle:0.16.6 \
  format --cluster=0 --replica=0 --replica-count=1 /data/0_0.tigerbeetle
```

> **Critical:** TigerBeetle data files must be initialized before starting. The format command only needs to run once.

---

### 4.12 Temporal (Workflow Orchestration)

**Purpose:** Orchestrates long-running workflows — loan processing, KYC verification, insurance claims, crop insurance payouts, multi-step payment flows.

**Image:** `temporalio/auto-setup:1.23.1`

```yaml
temporal:
  image: temporalio/auto-setup:1.23.1
  container_name: farmer-temporal
  restart: unless-stopped
  ports:
    - "7233:7233"
  environment:
    DB: postgresql
    DB_PORT: 5432
    POSTGRES_USER: ${DB_USER:-farmer_user}
    POSTGRES_PWD: ${DB_PASSWORD}
    POSTGRES_SEEDS: postgres
    DYNAMIC_CONFIG_FILE_PATH: config/dynamicconfig/development.yaml
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "tctl --address temporal:7233 cluster health || exit 1"]
    interval: 15s
    timeout: 10s
    retries: 10
    start_period: 30s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "1.0"
  networks:
    - farmconnect-network

temporal-ui:
  image: temporalio/ui:2.26.2
  container_name: farmer-temporal-ui
  restart: unless-stopped
  ports:
    - "8233:8080"
  environment:
    TEMPORAL_ADDRESS: temporal:7233
  depends_on:
    - temporal
  healthcheck:
    test: ["CMD-SHELL", "wget --quiet --tries=1 --spider http://localhost:8080 || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - farmconnect-network
```

---

### 4.13 Dapr (Distributed Application Runtime)

**Purpose:** Sidecar runtime providing state management, pub/sub, service invocation, and distributed locking across polyglot services.

**Image:** `daprio/dapr:1.13.0`

```yaml
dapr-placement:
  image: daprio/dapr:1.13.0
  container_name: farmer-dapr-placement
  restart: unless-stopped
  command: ["./placement", "--port", "50005"]
  ports:
    - "50005:50005"
  healthcheck:
    test: ["CMD-SHELL", "nc -z localhost 50005 || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 256M
  networks:
    - farmconnect-network
```

**To add Dapr sidecars to application services**, add to each service definition:
```yaml
labels:
  dapr.io/enabled: "true"
  dapr.io/app-id: "my-service"
  dapr.io/app-port: "8080"
```

---

### 4.14 Mojaloop (Payment Interoperability)

**Purpose:** Open-source payment switching layer for mobile money interoperability. Enables cross-provider payments (M-Pesa, MTN MoMo, Airtel Money).

**Image:** `mojaloop/simulator:latest`

```yaml
mojaloop-simulator:
  image: mojaloop/simulator:latest
  container_name: farmer-mojaloop
  restart: unless-stopped
  ports:
    - "8444:8444"
  environment:
    PARTIES_ENDPOINT: http://mojaloop-simulator:8444
    LOG_LEVEL: info
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:8444/health || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 512M
  networks:
    - farmconnect-network
```

> **Production:** Replace the simulator with a full Mojaloop Hub deployment or connect to your payment provider's Mojaloop-compatible endpoint.

---

## 5. Observability Stack

### 5.1 Prometheus (Metrics)

```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: farmer-prometheus
  restart: unless-stopped
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
    - prometheus-data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--storage.tsdb.retention.time=30d'
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
    interval: 10s
    timeout: 3s
    retries: 3
  networks:
    - farmconnect-network
```

### 5.2 Grafana (Dashboards)

```yaml
grafana:
  image: grafana/grafana:10.4.0
  container_name: farmer-grafana
  restart: unless-stopped
  ports:
    - "3100:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    GF_AUTH_ANONYMOUS_ENABLED: "false"
  volumes:
    - grafana-data:/var/lib/grafana
    - ./config/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
    - ./config/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
  depends_on:
    - prometheus
    - jaeger
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:3000/api/health || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - farmconnect-network
```

### 5.3 Jaeger (Distributed Tracing)

```yaml
jaeger:
  image: jaegertracing/all-in-one:1.54
  container_name: farmer-jaeger
  restart: unless-stopped
  ports:
    - "16686:16686"   # Jaeger UI
    - "14268:14268"   # Collector
    - "4317:4317"     # OTLP gRPC
    - "4318:4318"     # OTLP HTTP
  environment:
    COLLECTOR_OTLP_ENABLED: "true"
    SPAN_STORAGE_TYPE: memory       # Use "elasticsearch" or "opensearch" in prod
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:14269/"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - farmconnect-network
```

### 5.4 Loki + Promtail (Log Aggregation)

```yaml
loki:
  image: grafana/loki:2.9.3
  container_name: farmer-loki
  restart: unless-stopped
  ports:
    - "3101:3100"
  volumes:
    - ./config/loki/loki-config.yml:/etc/loki/local-config.yaml:ro
    - loki-data:/loki
  command: -config.file=/etc/loki/local-config.yaml
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:3100/ready"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - farmconnect-network

promtail:
  image: grafana/promtail:2.9.3
  container_name: farmer-promtail
  restart: unless-stopped
  volumes:
    - ./config/promtail/promtail-config.yml:/etc/promtail/config.yml:ro
    - /var/log:/var/log:ro
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
  command: -config.file=/etc/promtail/config.yml
  depends_on:
    - loki
  networks:
    - farmconnect-network
```

### 5.5 HashiCorp Vault (Secrets Management)

```yaml
vault:
  image: hashicorp/vault:1.15
  container_name: farmer-vault
  restart: unless-stopped
  ports:
    - "8200:8200"
  environment:
    VAULT_ADDR: "http://0.0.0.0:8200"
    VAULT_API_ADDR: "http://vault:8200"
  volumes:
    - vault-data:/vault/data
  cap_add:
    - IPC_LOCK
  healthcheck:
    test: ["CMD", "vault", "status"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - farmconnect-network
```

> **Production:** Use `vault server -config=/vault/config/config.hcl` with file or Consul backend, not dev mode.

---

## 6. Application Services

### 6.1 Main API (TypeScript/Node.js)

**Dockerfile:** Multi-stage build with `node:22-alpine`, pnpm, non-root user.

```yaml
app:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: farmer-app
  restart: unless-stopped
  ports:
    - "3000:3000"
  environment:
    NODE_ENV: production
    DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@pgbouncer:6432/farmer_data
    REDIS_HOST: redis
    REDIS_PORT: 6379
    REDIS_PASSWORD: ${REDIS_PASSWORD}
    KAFKA_BROKERS: kafka:9092
    KEYCLOAK_URL: http://keycloak:8080
    PERMIFY_ENDPOINT: http://permify:3476
    OPENSEARCH_URL: http://opensearch:9200
    TEMPORAL_ADDRESS: temporal:7233
    TIGERBEETLE_ADDRESS: tigerbeetle:3000
    MOJALOOP_API_URL: http://mojaloop-simulator:8444
    DAPR_HOST: dapr-placement
    DAPR_HTTP_PORT: 3500
    JWT_SECRET: ${JWT_SECRET}
    APISIX_ADMIN_URL: http://apisix:9180
    FLUVIO_URL: http://fluvio:9003
    OPENAPPSEC_URL: http://openappsec:8080
    # Polyglot service URLs
    FEATURE_FLAGS_SERVICE_URL: http://feature-flags:8101
    TILE_CACHE_URL: http://tile-cache:8097
    GO_WEBSOCKET_SERVICE_URL: http://gps-streaming:8098
    SPATIAL_QUERY_SERVICE_URL: http://spatial-queries:8099
    GEOCODING_SERVICE_URL: http://geocoding:8100
    SEARCH_SERVICE_URL: http://search-proxy:8104
    WAF_SERVICE_URL: http://waf-security:8105
    FLUVIO_SERVICE_URL: http://fluvio-streaming:8106
    WEATHER_SERVICE_URL: http://weather-alerts:8107
    CREDIT_SCORING_SERVICE_URL: http://credit-scoring:8108
    VOICE_SERVICE_URL: http://voice-navigation:8109
    ML_SERVICE_URL: http://ml-service:8001
    WHATSAPP_SERVICE_URL: http://whatsapp-service:8102
    BLOCKCHAIN_PROVENANCE_SERVICE_URL: http://blockchain-provenance-go:8110
    URBAN_DELIVERY_SERVICE_URL: http://urban-delivery-rust:8111
    CEA_AI_SERVICE_URL: http://cea-ai-python:8112
    AQUACULTURE_POND_SERVICE_URL: http://aquaculture-pond-go:8113
    AQUACULTURE_FEED_SERVICE_URL: http://aquaculture-feed-rust:8114
    AQUACULTURE_AI_SERVICE_URL: http://aquaculture-ai-python:8115
    CONTRACT_FARMING_SERVICE_URL: http://contract-farming-go:8116
    WAREHOUSE_RECEIPT_SERVICE_URL: http://warehouse-receipt-rust:8117
    CONVERSATIONAL_COMMERCE_SERVICE_URL: http://conversational-commerce-python:8118
    DEFAULT_CURRENCY: NGN
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:3000/api/health || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 15s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "2.0"
  networks:
    - farmconnect-network
```

**Build:**
```bash
docker build -t farmconnect/api:latest .
```

---

### 6.2 Go Microservices (17 services)

All Go services follow the same multi-stage pattern: `golang:1.22-alpine` builder → `alpine:3.19` runtime.

| Service | Directory | Port | Purpose |
|---------|-----------|------|---------|
| feature-flags | `services/feature-flags/` | 8101 | Feature toggle management |
| whatsapp-service | `services/whatsapp-service/` | 8102 | WhatsApp Business API |
| qr-traceability | `services/qr-traceability/` | 8103 | QR code supply chain |
| tile-cache | `services/tile-cache/` | 8097 | Map tile caching (Redis) |
| gps-streaming | `services/gps-streaming/` | 8098 | Real-time GPS WebSocket |
| blockchain-provenance | `services/go/blockchain-provenance/` | 8110 | Hyperledger verification |
| aquaculture-pond | `services/go/aquaculture-pond/` | 8113 | Pond monitoring |
| contract-farming | `services/go/contract-farming/` | 8116 | Contract lifecycle |
| equipment-fleet | `services/go/equipment-fleet-service/` | 8098 | Fleet management |
| loan-orchestrator | `services/go/loan-orchestrator/` | — | Loan workflow |
| image-service | `services/go/image-service/` | — | Image processing |
| realtime-service | `services/go/realtime-service/` | — | WebSocket hub |
| dapr-service | `services/go/dapr-service/` | — | Dapr state store |
| delivery-service | `services/go/delivery-service/` | — | Last-mile delivery |
| drone-service | `services/go/drone-service/` | — | Drone fleet control |
| supply-chain-service | `services/go/supply-chain-service/` | — | Supply chain tracking |
| tigerbeetle-service | `services/go/tigerbeetle-service/` | — | TB sidecar |

**Generic Dockerfile pattern:**
```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /service .

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /service /usr/local/bin/service
EXPOSE 8XXX
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8XXX/health || exit 1
CMD ["service"]
```

**Build all Go services:**
```bash
for svc in feature-flags whatsapp-service qr-traceability tile-cache gps-streaming; do
  docker build -t farmconnect/$svc:latest ./services/$svc/
done

for svc in blockchain-provenance aquaculture-pond contract-farming equipment-fleet-service \
  loan-orchestrator image-service realtime-service dapr-service delivery-service \
  drone-service supply-chain-service tigerbeetle-service; do
  docker build -t farmconnect/$svc:latest ./services/go/$svc/
done
```

---

### 6.3 Rust Microservices (13 services)

All Rust services follow: `rust:1.77-alpine` builder → `alpine:3.19` runtime. Compiled to static binaries.

| Service | Directory | Port | Purpose |
|---------|-----------|------|---------|
| spatial-queries | `services/spatial-queries/` | 8099 | PostGIS spatial queries |
| search-proxy | `services/search-proxy/` | 8104 | OpenSearch proxy |
| waf-security | `services/waf-security/` | 8105 | WAF request scanning |
| fluvio-streaming | `services/fluvio-streaming/` | 8106 | Fluvio event processor |
| urban-delivery | `services/rust/urban-delivery/` | 8111 | Last-mile routing |
| aquaculture-feed | `services/rust/aquaculture-feed/` | 8114 | Feed optimization |
| warehouse-receipt | `services/rust/warehouse-receipt/` | 8117 | Receipt tokenization |
| image-processor | `services/rust/image-processor/` | — | Crop image analysis |
| iot-gateway | `services/rust/iot-gateway/` | — | IoT device ingestion |
| tokenization-service | `services/rust/tokenization-service/` | — | Asset tokenization |
| autonomous-ops | `services/rust/autonomous-ops/` | — | Farm automation |
| isobus-gateway | `services/rust/isobus-gateway/` | — | Equipment telemetry |
| openappsec-waf | `services/rust/openappsec-waf/` | — | WAF integration |

**Generic Dockerfile pattern:**
```dockerfile
FROM rust:1.77-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release && rm -rf src
COPY src ./src
RUN cargo build --release

FROM alpine:3.19
COPY --from=builder /app/target/release/service-name /usr/local/bin/service-name
EXPOSE 8XXX
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8XXX/health || exit 1
CMD ["service-name"]
```

**Build all Rust services:**
```bash
for svc in spatial-queries search-proxy waf-security fluvio-streaming; do
  docker build -t farmconnect/$svc:latest ./services/$svc/
done

for svc in urban-delivery aquaculture-feed warehouse-receipt image-processor \
  iot-gateway tokenization-service autonomous-ops isobus-gateway openappsec-waf; do
  docker build -t farmconnect/$svc:latest ./services/rust/$svc/
done
```

---

### 6.4 Python Microservices (23 services)

All Python services use FastAPI/uvicorn. Pattern: `python:3.11-slim` or `python:3.12-slim`.

| Service | Directory | Port | Purpose |
|---------|-----------|------|---------|
| geocoding | `services/geocoding/` | 8100 | Address → coordinates |
| weather-alerts | `services/weather-alerts/` | 8107 | Weather monitoring |
| credit-scoring | `services/credit-scoring/` | 8108 | Farmer credit scoring |
| voice-navigation | `services/voice-navigation/` | 8109 | Voice-first interface |
| ml-service | `ml-service/` | 8001 | ML model serving |
| cea-ai | `services/python/cea-ai/` | 8112 | Controlled env agriculture |
| aquaculture-ai | `services/python/aquaculture-ai/` | 8115 | Aquaculture optimization |
| conversational-commerce | `services/python/conversational-commerce/` | 8118 | Chatbot engine |
| price-prediction | `services/python/price-prediction-service/` | 8093 | Price forecasting |
| ollama-service | `services/python/ollama-service/` | — | LLM inference |
| lakehouse-service | `services/python/lakehouse-service/` | — | Data lakehouse ETL |
| weather-service | `services/python/weather-service/` | 8069 | Weather data |
| federated-learning | `services/python/federated-learning/` | — | Privacy ML |
| satellite-service | `services/python/satellite-service/` | — | Satellite imagery |
| kyc-verification | `services/python/kyc-verification/` | — | KYC pipeline |
| loan-worker | `services/python/loan-worker/` | — | Temporal worker |
| temporal-workflows | `services/python/temporal-workflows/` | — | Workflow definitions |
| messaging-analytics | `services/python/messaging-analytics/` | — | Message analytics |
| sync-analytics | `services/python/sync-analytics/` | — | Sync metrics |
| cold-chain-service | `services/python/cold-chain-service/` | — | Cold chain monitoring |
| indoor-farming-ai | `services/python/indoor-farming-ai/` | — | Indoor farming optimization |
| agri-llm | `services/python/agri-llm/` | — | Agricultural LLM |
| sedona-supply-chain | `services/python/sedona-supply-chain/` | — | Geospatial supply chain |

**Generic Dockerfile pattern:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8XXX
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8XXX/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8XXX"]
```

**Build all Python services:**
```bash
docker build -t farmconnect/ml-service:latest ./ml-service/

for svc in geocoding weather-alerts credit-scoring voice-navigation; do
  docker build -t farmconnect/$svc:latest ./services/$svc/
done

for svc in cea-ai aquaculture-ai conversational-commerce price-prediction-service \
  ollama-service lakehouse-service weather-service federated-learning satellite-service \
  kyc-verification loan-worker temporal-workflows messaging-analytics sync-analytics \
  cold-chain-service indoor-farming-ai agri-llm sedona-supply-chain; do
  docker build -t farmconnect/$svc:latest ./services/python/$svc/
done
```

---

## 7. Docker Compose — Full Production Stack

**Start order (automated by `depends_on`):**

```bash
# Start everything
docker compose -f docker-compose.yml up -d

# Or start in stages
docker compose up -d postgres redis kafka           # Layer 1: Data stores
docker compose up -d pgbouncer keycloak permify      # Layer 2: Auth + pooling
docker compose up -d opensearch apisix openappsec    # Layer 3: Search + gateway
docker compose up -d tigerbeetle temporal fluvio     # Layer 4: Financial + workflow
docker compose up -d dapr-placement mojaloop-simulator # Layer 5: Runtime
docker compose up -d prometheus grafana jaeger loki   # Layer 6: Observability
docker compose up -d app                              # Layer 7: Main API
# Layer 8: All polyglot microservices
docker compose up -d feature-flags whatsapp-service qr-traceability \
  tile-cache gps-streaming spatial-queries search-proxy waf-security \
  fluvio-streaming geocoding weather-alerts credit-scoring voice-navigation ml-service
```

---

## 8. Startup Order & Dependencies

```
Layer 1 (no deps):     PostgreSQL, Redis, Kafka
Layer 2 (needs PG):    PgBouncer, Keycloak, Permify, Temporal
Layer 3 (standalone):  OpenSearch, Fluvio, TigerBeetle, Dapr, Mojaloop
Layer 4 (needs Redis): APISIX
Layer 5 (standalone):  OpenAppSec, Vault
Layer 6 (needs PG+R):  Main API → depends on PostgreSQL + Redis (minimum)
Layer 7 (needs API):   Polyglot services (some need Kafka, Redis, PostgreSQL)
Layer 8 (needs all):   Prometheus, Grafana, Jaeger, Loki (scrape all services)
```

**Dependency graph (critical path):**
```
PostgreSQL ──→ PgBouncer ──→ Main API
           ──→ Keycloak
           ──→ Permify
           ──→ Temporal
Redis ─────→ APISIX
           ──→ Main API
           ──→ tile-cache, gps-streaming, ml-service
Kafka ─────→ whatsapp-service, weather-alerts
           ──→ Main API (event publishing)
OpenSearch ─→ search-proxy, opensearch-dashboards
```

---

## 9. Volume Management & Backups

### Named Volumes

```yaml
volumes:
  postgres-data:        # Database files (CRITICAL — backup daily)
  redis-data:           # Redis AOF + RDB snapshots
  kafka-data:           # Kafka log segments
  fluvio-data:          # Fluvio stream data
  opensearch-data:      # Search indices
  tigerbeetle-data:     # Financial ledger (CRITICAL — backup daily)
  prometheus-data:       # Metrics TSDB
  grafana-data:          # Dashboard configs
  loki-data:             # Log storage
  ml-models:             # ML model weights cache
  vault-data:            # Vault secrets storage (CRITICAL)
```

### Backup Scripts

```bash
# PostgreSQL — daily at 2 AM
docker exec farmer-postgres pg_dump -U farmer_user farmer_data | gzip > backup/pg_$(date +%Y%m%d).sql.gz

# Redis — every 6 hours
docker exec farmer-redis redis-cli -a $REDIS_PASSWORD BGSAVE
docker cp farmer-redis:/data/dump.rdb backup/redis_$(date +%Y%m%d_%H).rdb

# TigerBeetle — daily at 4 AM
docker stop farmer-tigerbeetle
docker cp farmer-tigerbeetle:/data/0_0.tigerbeetle backup/tb_$(date +%Y%m%d).tigerbeetle
docker start farmer-tigerbeetle
```

---

## 10. Environment Variables Reference

Create a `.env` file in the project root:

```bash
# ===== REQUIRED SECRETS =====
DB_USER=farmer_user
DB_PASSWORD=<strong-random-password>
REDIS_PASSWORD=<strong-random-password>
JWT_SECRET=<min-32-char-random-string>
KEYCLOAK_ADMIN_PASSWORD=<strong-password>
OPENSEARCH_PASSWORD=<strong-password>
GRAFANA_PASSWORD=<strong-password>
APISIX_ADMIN_KEY=<random-api-key>

# ===== EXTERNAL HOST =====
EXTERNAL_HOST=api.farmconnect.app
KEYCLOAK_HOSTNAME=auth.farmconnect.app

# ===== OPTIONAL API KEYS =====
OPENWEATHER_API_KEY=
META_WHATSAPP_ACCESS_TOKEN=
META_WHATSAPP_PHONE_NUMBER_ID=
STRIPE_SECRET_KEY=
PAYSTACK_SECRET_KEY=
AFRICASTALKING_API_KEY=

# ===== SMTP =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
```

---

## 11. Security Hardening Checklist

- [ ] **Change all default passwords** (postgres, keycloak admin, redis, grafana)
- [ ] **Enable Redis AUTH** (`requirepass` set)
- [ ] **Enable OpenSearch security plugin** with TLS
- [ ] **Keycloak:** Use `start --optimized` mode, set `KC_HOSTNAME`, enable HTTPS
- [ ] **APISIX:** Restrict admin API to internal network only (`:9180`)
- [ ] **TigerBeetle:** Bind only to internal network
- [ ] **Vault:** Initialize and unseal, enable audit logging
- [ ] **Docker:** Run containers as non-root where possible
- [ ] **Network:** Use Docker network isolation — no `ports` exposure for internal services
- [ ] **TLS:** Mount SSL certificates for APISIX, Keycloak, and NGINX ingress
- [ ] **Secrets:** Use Docker secrets or Vault — never store in `.env` in production
- [ ] **Firewall:** Only expose ports 80, 443 (APISIX) externally

---

## 12. Scaling Guide

| Component | Horizontal Scaling | Notes |
|-----------|-------------------|-------|
| Main API | `docker compose up --scale app=3` | Stateless — scale freely behind APISIX |
| Go services | Scale per service | Stateless — scale independently |
| Rust services | Scale per service | Very low memory footprint |
| Python ML | Scale with GPU | Attach GPU volumes for model inference |
| PostgreSQL | Read replicas | Use streaming replication |
| Redis | Redis Cluster | 3-node minimum for HA |
| Kafka | Add brokers | Increase `KAFKA_CFG_DEFAULT_REPLICATION_FACTOR` |
| OpenSearch | Add nodes | Change `discovery.type` from `single-node` to cluster |
| Keycloak | Scale horizontally | Requires shared DB + Infinispan cache |

**Quick scale command:**
```bash
docker compose up -d --scale app=3 --scale feature-flags=2 --scale ml-service=2
```

---

## Quick Start — Full Stack in One Command

```bash
# 1. Clone the repo
git clone https://github.com/munisp/farmer-data-collection.git
cd farmer-data-collection

# 2. Create environment file
cp .env.example .env
# Edit .env with real passwords

# 3. Initialize TigerBeetle (first time only)
docker volume create tigerbeetle-data
docker run --rm -v tigerbeetle-data:/data \
  ghcr.io/tigerbeetle/tigerbeetle:0.16.6 \
  format --cluster=0 --replica=0 --replica-count=1 /data/0_0.tigerbeetle

# 4. Start everything
docker compose up -d

# 5. Seed the database
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed.sql
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed-extended.sql
docker exec -i farmer-postgres psql -U farmer_user -d farmer_data < drizzle/seed-remaining.sql

# 6. Verify health
docker compose ps
curl http://localhost:3000/api/health
curl http://localhost:9090/-/healthy      # Prometheus
curl http://localhost:9200/_cluster/health # OpenSearch
```

**Access points:**

| Service | URL |
|---------|-----|
| Main API | http://localhost:3000 |
| APISIX Gateway | http://localhost:9080 |
| Keycloak Admin | http://localhost:8080 |
| Temporal UI | http://localhost:8233 |
| Grafana | http://localhost:3100 |
| Prometheus | http://localhost:9090 |
| OpenSearch Dashboards | http://localhost:5601 |
| Jaeger UI | http://localhost:16686 |
| Vault | http://localhost:8200 |

---

*Generated for FarmConnect Platform v12 — 14 middleware + 53 polyglot services*
