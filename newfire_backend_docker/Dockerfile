FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund

FROM node:22-alpine
WORKDIR /app
RUN apk add --no-cache wget && \
    addgroup -g 10001 nfire && \
    adduser -D -u 10001 -G nfire nfire
COPY --from=deps --chown=nfire:nfire /app/node_modules ./node_modules
COPY --chown=nfire:nfire . .
USER nfire
EXPOSE 3200
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --spider -q http://127.0.0.1:3200/health || exit 1
CMD ["node", "src/server.js"]
