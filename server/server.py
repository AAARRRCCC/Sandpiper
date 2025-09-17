import asyncio
import json
import time

async def handle_client(reader, writer):
    
    # take one input line, as utf-8, cut off the newline, and print as a python string
    data = await reader.readline()
    if not data:
        return
    line = data.decode("utf-8", errors="replace").rstrip("\n")
    print(f"RAW: {line}")


    # try to turn incoming JSON into python dict
    # if it fails, send error, if it works, send acknowledgment
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        err = {"type": "error", "text": "invalid json"}
        writer.write((json.dumps(err) + "\n").encode("utf-8")) # queue up bytes to the socket
        await writer.drain() # flush the queue
        writer.close()
        await writer.wait_closed()
        return # close cleanly after one message

    ack = {"type": "notice", "text": "ok", "ts": int(time.time())}
    writer.write((json.dumps(ack) + "\n").encode("utf-8"))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, host="0.0.0.0", port=5000)
    print("Server started on 0.0.0.0:5000")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())