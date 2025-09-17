import asyncio
import json
import time

clients = set() # global state

async def handle_client(reader, writer):
    nick = "anon" # per-connection state
    clients.add(writer)
    try:
        while True: 
            data = await reader.readline()
            if not data: # close client
                break
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
                continue
            
            t = obj.get("type")
            if t == "nick":
                nick = obj.get("nick", "anon")
                reply = {"type":"notice","text":f"nick = {nick}","ts":int(time.time())}
            elif t == "msg":
                text = obj.get("text", "")
                print(f"{nick}: {text}") #logging
                # broadcasts to all clients INCLUDING sender (so they can see it obviously)
                out = {"type":"msg","nick":nick,"text":text,"ts":int(time.time())}
                for w in list(clients):
                    w.write((json.dumps(out) + "\n").encode("utf-8"))
                await asyncio.gather(*(w.drain() for w in list(clients)), return_exceptions=True) # flush all clients

                reply = {"type":"notice","text":"ok","ts":int(time.time())}
            else:
                reply = {"type":"error","text":"invalid message type","ts":int(time.time())}

            writer.write((json.dumps(reply) + "\n").encode("utf-8"))
            await writer.drain()

    finally:
        clients.discard(writer)
        writer.close()
        await writer.wait_closed()




async def main():
    server = await asyncio.start_server(handle_client, host="0.0.0.0", port=5000)
    print("Server started on 0.0.0.0:5000")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())