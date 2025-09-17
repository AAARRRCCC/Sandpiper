import asyncio
import json
import time

async def handle_client(reader, writer):
    data = await reader.readline()
    if not data:
        return
    line = data.decode("utf-8", errors="replace").rstrip("\n")
    print(f"RAW: {line}")


async def main():
    server = await asyncio.start_server(handle_client, host="0.0.0.0", port=5000)
    print("Server started on 0.0.0.0:5000")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())