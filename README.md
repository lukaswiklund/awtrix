# awtrix

Pushes three custom apps to an AWTRIX 3 device (Ulanzi TC001):

| app       | shows                                                 |
| --------- | ----------------------------------------------------- |
| `bg`      | current Dexcom G7 glucose + trend arrow, colour-coded |
| `claude`  | Claude usage: percent of the 5h window, time to reset |
| `claudew` | the same for the 7-day window, marked with a `w`      |

> **Not a medical device.** Dexcom Share is an undocumented API, readings lag
> the sensor by several minutes, and this bridge can silently stall. Do not
> make treatment decisions from the clock. Keep the real Dexcom app as your
> alarm.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env      # then fill in AWTRIX_IP and your Dexcom login
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

The container runs as uid 1000 and mounts `~/.claude` read-only so the Claude
app can read the OAuth token — if that uid does not own
`~/.claude/.credentials.json` on the host (it is 0600), adjust `user:` in
[compose.yml](compose.yml) or the claude app will show `CC?`. `AWTRIX_IP` and
the Dexcom credentials come from `.env` via `env_file`. Nothing is published; the bridge
only makes outbound connections to the device on the LAN.

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

The `claude` and `claudew` apps read your subscription limits (the percentages
`/usage` shows) from Anthropic's account endpoint, reusing the OAuth token
Claude Code already stores — on macOS in the login keychain, so the first run
triggers a keychain prompt; elsewhere from `~/.claude/.credentials.json`. That
endpoint is internal and undocumented: if it changes shape the `claude` app
falls back to showing `CC?` and `claudew` disappears.

The two windows get their own frames rather than sharing one: `24% 2h13 19%w`
runs past the 32px display and scrolls, so the 5h percent ends up off-screen
half the time.

## Layout

```text
awtrix/
  config.py     settings, thresholds, colours — edit here to tune
  transport.py  HTTP to the device (push_app / notify / indicator)
  dexcom.py     Share client, bg payload, urgent-low alarm
  claude.py     OAuth token, usage endpoint, claude payload
  icons.py      icon upload
  cli.py        argument parsing and the poll loop
icons/          8x8 droplet icons, one per glucose range
run.py          entrypoint
compose.yml     production deployment (see Dockerfile)
```
