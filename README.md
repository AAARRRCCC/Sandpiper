# Sandpiper

Sandpiper is a minimal terminal chat system. A Python relay server runs on a host (e.g., a ThinkPad) and CLI clients connect over raw TCP. When port-forwarding isn’t possible, an `ngrok tcp` tunnel exposes the server so friends can join from anywhere.

> Status: early WIP. This README will expand as I implement features.

## Goals
- Simple: Python 3.10+ with asyncio TCP sockets
- Portable: runs on Linux/macOS/Windows terminals
- Reachable: works over LAN or via `ngrok tcp`
- Minimal protocol: newline-delimited JSON messages

## Repo Layout
```
.
├── server/
│   └── server.py
├── client/
│   └── client.py
├── requirements.txt
├── README.md
└── chat_project_roadmap.md
```

## Quick Start (Local LAN)
1. Optional venv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
2. Start the server (example port 5000):
   ```bash
   python3 server/server.py --host 0.0.0.0 --port 5000
   ```
3. Connect from another terminal/machine:
   ```bash
   python3 client/client.py --host <SERVER_LAN_IP> --port 5000 --nick alice
   ```

## Quick Start (Over the Internet via ngrok TCP)
On the server host:
```bash
python3 server/server.py --host 0.0.0.0 --port 5000
ngrok tcp 5000
```
ngrok will print something like:
```
Forwarding  tcp://2.tcp.ngrok.io:17832 -> localhost:5000
```
Clients connect using **exactly** that host and port:
```bash
python3 client/client.py --host 2.tcp.ngrok.io --port 17832 --nick alice
```

## Minimal Protocol
One JSON object per line (UTF-8):
```
{"type":"msg","nick":"alice","text":"hello","ts":1731812345}
```
This may evolve (see roadmap).

## Roadmap
See `sandpiper_roadmap.md` for the step-by-step plan.

## License
MIT License. Free to use and modify.
