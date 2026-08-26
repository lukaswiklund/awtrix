FROM node:22-slim AS codex-cli

ARG CODEX_VERSION=0.149.1
ARG TARGETARCH

# The npm package carries a platform-specific native bundle. Copy only that
# bundle into the runtime image; Node and npm are not needed there. Keep the
# companion code-mode host and resources beside the main binary because the
# app server resolves them relative to its own installation.
RUN npm install --global "@openai/codex@${CODEX_VERSION}" \
    && case "$TARGETARCH" in \
         amd64) package=codex-linux-x64; target=x86_64-unknown-linux-musl ;; \
         arm64) package=codex-linux-arm64; target=aarch64-unknown-linux-musl ;; \
         *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && cp -R "/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/${package}/vendor/${target}" /codex

FROM python:3.13-slim

# HOME matters: claude.py resolves the credentials file through ~, and the
# container reads it from a mount at $HOME/.claude.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/app

# uid 1000 so the read-only ~/.claude mount is readable (it is 0600 on the host).
RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=codex-cli /codex /opt/codex
RUN ln -s /opt/codex/bin/codex /usr/local/bin/codex

COPY awtrix/ ./awtrix/
COPY icons/ ./icons/
COPY run.py ./

USER app

ENTRYPOINT ["python", "-m", "awtrix"]
