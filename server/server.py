import asyncio
import json
import time

clients = set() # global state

async def broadcast(obj):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    for w in list(clients):
        w.write(data)
    await asyncio.gather(*(w.drain() for w in list(clients)), return_exceptions=True) # flush all clients

async def handle_client(reader, writer):
    nick = "anon" # per-connection state
    clients.add(writer)
    await broadcast({"type":"notice","text":f"{nick} joined","ts":int(time.time())})

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
                writer.write((json.dumps(reply) + "\n").encode("utf-8"))
                await writer.drain()
            elif t == "msg":
                text = obj.get("text", "")
                print(f"{nick}: {text}") #logging
                # broadcasts to all clients INCLUDING sender (so they can see it obviously)
                out = {"type":"msg","nick":nick,"text":text,"ts":int(time.time())}
                await broadcast(out)
            else:
                err = {"type":"error","text":"invalid message type","ts":int(time.time())}
                writer.write((json.dumps(err) + "\n").encode("utf-8"))
                await writer.drain()

            
    finally:
        await broadcast({"type":"notice","text":f"{nick} left","ts":int(time.time())})
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