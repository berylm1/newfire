FROM node:20-bookworm-slim

ARG TTYD_VERSION=1.7.7

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git ripgrep jq tini tmux \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
         -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd \
    && npm install -g codeep@2.1.1 \
    && npm cache clean --force

RUN mkdir -p /workspace /home/node/.config/codeep /home/node/.config/codeep-nodejs \
    && chown -R node:node /workspace /home/node/.config

COPY --chown=node:node codeep-config.json /home/node/.config/codeep/config.json
COPY --chown=node:node codeep-config.json /home/node/.config/codeep-nodejs/config.json

USER node
WORKDIR /workspace

ENV NODE_ENV=production \
    TERM=xterm-256color \
    OPENAI_BASE_URL=http://192.168.1.158:8000/v1

EXPOSE 7681

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["ttyd", "-W", "-p", "7681", "-i", "0.0.0.0", "tmux", "new-session", "-A", "-s", "codeep", "codeep"]
