# awtrix

Pushes custom apps to an AWTRIX 3 device (Ulanzi TC001):

| app       | shows                                                 |
| --------- | ----------------------------------------------------- |
| `bg`      | current Dexcom G7 glucose + trend arrow, colour-coded |
| `claude`  | Claude usage: percent of the 5h window, time to reset |
| `claudew` | the same for the 7-day all-models window              |
| `claudef` | the same for the 7-day Fable window                   |
| `codex`   | Codex usage for the short rolling window              |
| `codexw`  | Codex usage for the weekly window                     |

> **Not a medical device.** Dexcom Share is an undocumented API, readings lag
> the sensor by several minutes, and this bridge can silently stall. Do not
> make treatment decisions from the clock. Keep the real Dexcom app as your
> alarm.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env      # then fill in AWTRIX_IP, your Dexcom login, and
                          # (for Docker) CLAUDE_DIR and CODEX_DIR
```

Upload the droplet icons to the device once (or after a reflash):

```bash
./venv/bin/python run.py --install-icons
```

## Run

```bash
./venv/bin/python run.py             # run forever
./venv/bin/python run.py --once      # single pass, for testing
./venv/bin/python run.py --selftest  # dummy values, no credentials needed
./venv/bin/python run.py -v          # debug logging
```

`python -m awtrix` works too.

## Production (Docker)

```bash
docker compose up -d --build
docker compose logs -f
```

The container mounts `$CLAUDE_DIR/.claude` read-only for Claude and
`$CODEX_DIR/.codex` read-write for Codex, and runs as uid 1000. Three things
make the Claude frame show `CC?`:

- **`CLAUDE_DIR` unset or wrong.** Set it in `.env` to the home directory
  holding `.claude`. It is not `$HOME` because `sudo docker compose` resolves
  that to `/root` and Docker silently mounts an empty `/root/.claude`; compose
  now refuses to start rather than mount the wrong path.
- **uid mismatch.** `~/.claude/.credentials.json` is 0600, so if uid 1000 does
  not own it on the host, adjust `user:` in [compose.yml](compose.yml).
- **Token expired.** Claude Code only rotates the token while it is running,
  so after a quiet evening `.credentials.json` holds an expired `accessToken`
  and the endpoint returns 401 until the next `claude` session. On the machine
  that owns `CLAUDE_DIR`, install the timer that runs a trivial `claude -p`
  whenever the token is expired or has under 30 minutes left:

  ```bash
  cp scripts/systemd/claude-token-refresh.* ~/.config/systemd/user/
  systemctl --user daemon-reload
  systemctl --user enable --now claude-token-refresh.timer
  loginctl enable-linger $USER   # keep user timers running when logged out
  ```

  Adjust `ExecStart` in the service if the repo is not at `~/code/awtrix`.
  Check with `systemctl --user list-timers` and
  `journalctl --user -u claude-token-refresh`.

`AWTRIX_IP` and the Dexcom credentials come from `.env` via `env_file`. Nothing
is published; the bridge only makes outbound connections to the device on the
LAN.

The Codex mount must be writable because the Codex CLI owns OAuth refresh and
atomically replaces `auth.json`. Set `CODEX_DIR` to the home directory where
`codex login` was run. A missing CLI/login or unreadable mount shows `CX?`.

One-off commands use the same image:

```bash
docker compose run --rm awtrix --install-icons
docker compose run --rm awtrix --selftest
```

## Configuration

The device address (`AWTRIX_IP`) and the Dexcom credentials live in `.env`
(loaded at startup; real environment variables take precedence). Everything
else — Share region, glucose thresholds and units, poll intervals, icons,
colours — is a literal in [awtrix/config.py](awtrix/config.py). Edit that file
to change behaviour.

## Claude usage

The `claude`, `claudew` and `claudef` apps read your subscription limits (the
percentages `/usage` shows) from Anthropic's account endpoint, reusing the
OAuth token Claude Code already stores — on macOS in the login keychain, so the
first run triggers a keychain prompt; elsewhere from
`~/.claude/.credentials.json`. That endpoint is internal and undocumented: if
it changes shape the `claude` app falls back to showing `CC?` and the other two
disappear.

It is polled every `USAGE_POLL` seconds and rate-limited by Anthropic, shared
with Claude Code's own polling. A failed poll doubles the gap (honouring
`Retry-After`) up to `USAGE_BACKOFF_MAX`, so a `429` clears itself instead of
being renewed by the retries; the last good numbers stay on screen meanwhile.

Each window gets its own frame rather than sharing one: `24% 2h13 19%w` runs
past the 32px display and scrolls, so the 5h percent ends up off-screen half
the time. The frames otherwise look identical, so the percent's colour says
which window is showing — white for the 5h, blue for the 7-day, orange for
Fable — while the progress bar keeps the green/yellow/red severity colour.

## Codex usage

The `codex` and `codexw` apps ask the local
[Codex app server](https://developers.openai.com/codex/app-server) for the
ChatGPT rate-limit windows. This is the supported interface used by Codex
clients; the bridge does not parse or send the OAuth token itself. It
identifies short and weekly windows from their reported durations, since some
plans expose only one window. Missing windows disappear instead of leaving
stale values behind.

Codex usage is polled every five minutes with exponential backoff on failures,
while the countdown is refreshed every minute from cached reset timestamps.
Green percent text identifies the short window and purple identifies weekly;
the progress bar still uses green/yellow/red for utilization severity.

Usage frames whose displayed utilization is `0%` are removed until usage rises
above zero. Fetch failures remain visible as `CC?` or `CX?` error frames.

## Layout

```text
awtrix/
  config.py     settings, thresholds, colours — edit here to tune
  transport.py  HTTP to the device (push_app / notify / indicator)
  dexcom.py     Share client, bg payload, urgent-low alarm
  claude.py     OAuth token, usage endpoint, claude payload
  codex.py      Codex app-server client, usage cache, codex payload
  icons.py      icon upload
  cli.py        argument parsing and the poll loop
icons/          8x8 droplet icons, one per glucose range
run.py          entrypoint
compose.yml     production deployment (see Dockerfile)
```
