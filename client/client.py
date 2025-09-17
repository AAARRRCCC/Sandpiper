import asyncio
import json
import argparse
import contextlib

async def recv_loop(reader):
    while True:
        data = await reader.readline()
        if not data:
            print("server closed") # clean shutdown
            break
        line = data.decode("utf-8", errors="replace").rstrip("\n")
        print(line)

async def send_loop(writer):
    while True:
        text = await asyncio.to_thread(input) # doesnt block event loop
        if text.strip() == "/quit":
            break
        msg = {"type": "msg", "text": text}
        writer.write((json.dumps(msg) + "\n").encode("utf-8"))
        await writer.drain()

async def main(host, port, nick):
    reader, writer = await asyncio.open_connection(host, port)
    print(f"connected to {host}:{port}")
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
    p = argparse.ArgumentParser() # requires host and port args, then connects with them
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--nick")
    args = p.parse_args()
    asyncio.run(main(args.host, args.port, args.nick))