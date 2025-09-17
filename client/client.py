import asyncio
import argparse

async def main(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    print(f"connected to {host}:{port}")
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("server closed connection") # clean shutdown
                break
            line = data.decode("utf-8", errors="replace").rstrip("\n")
            print(line)
    finally:
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    p = argparse.ArgumentParser() # requires host and port args, then connects with them
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    args = p.parse_args()
    asyncio.run(main(args.host, args.port))