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

COPY awtrix/ ./awtrix/
COPY icons/ ./icons/
COPY run.py ./

USER app

ENTRYPOINT ["python", "-m", "awtrix"]
