# Terminal Chat Project Roadmap

## 1. Decide scope & tech
- Pick language/runtime (**Python 3.10+**, `asyncio`).
- Model: **relay server** on ThinkPad; simple TCP clients on user machines.
- Outcome: clear stack + repo skeleton.

## 2. Design the minimal protocol
- Framing: **newline-delimited** messages (simple) or **length-prefixed** (robust).
- Message shape: tiny JSON (`{type, nick, text, ts}`).
- Outcome: 1-pager specifying message rules & special commands (`/nick`, `/quit`).

## 3. MVP server (local only)
- Accept multiple clients, broadcast line-framed messages, handle disconnects.
- Basic features: nicknames, join/leave notices, `/quit`.
- Outcome: chat works locally with two terminals on the same machine.

## 4. CLI client (local)
- Connects to host/port, reads stdin, prints messages with timestamps.
- Quality of life: colors, simple `/nick`, Ctrl-C clean exit.
- Outcome: two local clients can chat via the local server.

## 5. Expose over the internet (ngrok TCP)
- Run server on `0.0.0.0:5000`; `ngrok tcp 5000`; copy **exact** host:port (e.g., `2.tcp.ngrok.io:XXXXX`).
- Outcome: a friend connects from anywhere and chats end-to-end.

## 6. Resilience & polish
- Robust reads/writes (partial reads), timeouts, keep-alive, simple rate-limit.
- Server logging (rotating file), basic `/who` command.
- Outcome: fewer crashes, easier debugging.

## 7. Security baseline (lightweight)
- Shared **room code** required on connect (pre-shared).
- Optional: app-level encryption (e.g., **NaCl box** or TLS via `ssl`).
- Outcome: not public-by-default; basic privacy.

## 8. Packaging & run-forever
- **systemd** unit for server; separate unit for `ngrok tcp`.
- Optional single-file builds for client (PyInstaller) for Windows/Linux.
- Outcome: ThinkPad auto-starts the chat server and tunnel on boot.

## 9. (Optional) Nice-to-haves
- One-time pairing codes (croc-style), multi-rooms, admin commands, logs viewer.
- Swap ngrok for Cloudflare Tunnel or a cheap VPS reverse-SSH later.
