import asyncio
import json
import argparse
import contextlib
from datetime import datetime
import os
import hashlib
import colorsys

# ANSI basics
C_RESET = "\033[0m"
C_BOLD  = "\033[1m"
C_RED   = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW= "\033[33m"
C_BLUE  = "\033[34m"

# Cache so we don't recompute per message
_COLOR_CACHE: dict[str, str] = {}

def _supports_truecolor() -> bool:
    ct = os.environ.get("COLORTERM", "").lower()
    return "truecolor" in ct or "24bit" in ct

def _nick_color_code(nick: str) -> str:
    """Stable 'random' color per nick using hash→HLS→RGB. 24-bit if possible, else 256-color."""
    if not nick:
        return C_BLUE

    if nick in _COLOR_CACHE:
        return _COLOR_CACHE[nick]

    # Stable 32-bit hash
    hbytes = hashlib.blake2b(nick.encode("utf-8"), digest_size=4).digest()
    seed = int.from_bytes(hbytes, "big")

    # Hue from 0..359, with seeded saturation/lightness in readable ranges
    hue = seed % 360
    # colorsys uses H, L, S in [0,1]
    # Keep lightness mid and saturation fairly high for readability
    sat = 0.70 + ((seed >> 10) & 0x7) / 31.0 * 0.15   # 0.70..0.85
    lig = 0.50 + ((seed >> 17) & 0x7) / 31.0 * 0.10   # 0.50..0.60

    r, g, b = colorsys.hls_to_rgb(hue/360.0, lig, sat)
    R, G, B = int(r*255), int(g*255), int(b*255)

    if _supports_truecolor():
        code = f"\033[38;2;{R};{G};{B}m"
    else:
        # Map to ANSI 256 color cube (16..231). Avoid too-dark/grayscale.
        def to_ansi_step(v: int) -> int:
            return max(1, min(5, round(v/255*5)))  # clamp 1..5 to avoid near-black
        r5, g5, b5 = to_ansi_step(R), to_ansi_step(G), to_ansi_step(B)
        idx = 16 + 36*r5 + 6*g5 + b5
        code = f"\033[38;5;{idx}m"

    _COLOR_CACHE[nick] = code
    return code

def format_message(obj):
    ts = datetime.fromtimestamp(obj.get('ts', 0)).strftime('%H:%M:%S')
    nick = obj.get('nick', '')
    text = obj.get('text', '')
    msg_type = obj.get('type', '')

    if msg_type == 'msg':
        color_code = _nick_color_code(nick)
        return f"<{ts}> {color_code}{C_BOLD}{nick}{C_RESET}: {text}"
    elif msg_type == 'notice':
        return f"<{ts}> {C_YELLOW}* {text} *{C_RESET}"
    elif msg_type == 'nick':
        return f"<{ts}> {C_GREEN}* {text} *{C_RESET}"
    elif msg_type == 'error':
        return f"<{ts}> {C_RED}! error: {text}{C_RESET}"
    else:
        return json.dumps(obj)

async def recv_loop(reader):
    while True:
        data = await reader.readline()
        if not data:
            print("server closed")  # clean shutdown
            break
        line = data.decode("utf-8", errors="replace").rstrip("\n")
        try:
            obj = json.loads(line)
            print(format_message(obj))
        except json.JSONDecodeError:
            print(f"{C_RED}! invalid data from server: {line}{C_RESET}")

async def send_loop(writer):
    while True:
        text = await asyncio.to_thread(input)  # doesnt block event loop
        print("\033[1A\033[2K", end="", flush=True)
        if text.strip() == "/quit":
            break
        msg = {"type": "msg", "text": text}
        writer.write((json.dumps(msg) + "\n").encode("utf-8"))
        await writer.drain()

async def main(host, port, nick):
    reader, writer = await asyncio.open_connection(host, port)
    print(f"connected to {host}:{port}")
    print(format_message({"type":"notice","text":"Type /quit to exit"}))
    if nick:
        writer.write((json.dumps({"type": "nick", "nick": nick}) + "\n").encode("utf-8"))
        await writer.drain()

    # concurrently run send and receive loops
    send_task = asyncio.create_task(send_loop(writer))
    recv_task = asyncio.create_task(recv_loop(reader))
    done, pending = await asyncio.wait(
        [send_task, recv_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--nick")
    args = p.parse_args()
    asyncio.run(main(args.host, args.port, args.nick))
