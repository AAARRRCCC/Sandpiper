import asyncio
import json
import argparse
import contextlib

# --- Color and formatting utilities ---
C_RESET = "\033[0m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_CYAN = "\033[36m"

def format_message(obj):
    t = obj.get("type")
    if t == "msg":
        nick = obj.get("nick", "anon")
        text = obj.get("text", "")
        return f"{C_CYAN}{nick}{C_RESET}: {text}"
    elif t == "notice":
        return f"{C_YELLOW}[notice]{C_RESET} {obj.get('text','')}"
    elif t == "error":
        return f"{C_RED}[error]{C_RESET} {obj.get('text','')}"
    elif t == "nick":
        return f"{C_GREEN}[nick]{C_RESET} {obj.get('text','')}"
    else:
        return f"{C_RED}[?]{C_RESET} {obj}"

# --- P2P additions ---
peers = {}  # Track other clients: { (host, port): (reader, writer) }

async def connect_to_peer(host, port):
    # Make direct TCP connection to another client
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # Simple handshake: send our nick (or anon)
        nick = getattr(connect_to_peer, "nick", "anon")
        writer.write((json.dumps({"type": "hello", "nick": nick}) + "\n").encode("utf-8"))
        await writer.drain()
        # Wait for their hello
        data = await reader.readline()
        if not data:
            raise Exception("No handshake reply")
        obj = json.loads(data.decode("utf-8", errors="replace").rstrip("\n"))
        if obj.get("type") != "hello":
            raise Exception("Invalid handshake")
        peer_nick = obj.get("nick", "anon")
        peers[(host, port)] = (reader, writer)
        # Start receiving from this peer
        asyncio.create_task(peer_recv_loop(reader, (host, port), peer_nick))
    except Exception as e:
        print(f"[P2P] Error connecting to peer {host}:{port}: {e}")

async def broadcast_to_peers(message):
    # Send message to all connected peers
    data = (json.dumps(message) + "\n").encode("utf-8")
    for (host, port), (reader, writer) in list(peers.items()):
        try:
            writer.write(data)
            await writer.drain()
        except Exception as e:
            print(f"[P2P] Failed to send to {host}:{port}: {e}")
            # Optionally remove dead peer
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            peers.pop((host, port), None)

async def peer_recv_loop(reader, peer_addr, peer_nick):
    while True:
        try:
            data = await reader.readline()
            if not data:
                print(f"[P2P] Peer {peer_addr} disconnected")
                break
            line = data.decode("utf-8", errors="replace").rstrip("\n")
            try:
                obj = json.loads(line)
                print(format_message(obj))
            except json.JSONDecodeError:
                print(f"[P2P] Invalid data from {peer_addr}: {line}")
        except Exception as e:
            print(f"[P2P] Error in peer_recv_loop for {peer_addr}: {e}")
            break
    peers.pop(peer_addr, None)
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
    # For now, keep original client-server logic
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
    p.add_argument("--host")
    p.add_argument("--port", type=int)
    p.add_argument("--nick")
    # P2P options
    p.add_argument("--p2p", action="store_true", help="Enable P2P mode")
    p.add_argument("--bootstrap", action="store_true", help="Run as bootstrap peer (listen for others)")
    p.add_argument("--peer", action="append", help="Peer address host:port (can specify multiple)")
    args = p.parse_args()

    # For now, default to original client-server mode
    if not args.p2p:
        asyncio.run(main(args.host, args.port, args.nick))
    else:
        import sys

        async def p2p_main():
            # Set nick for handshake
            connect_to_peer.nick = args.nick or "anon"

            # If bootstrap, listen for incoming peer connections
            if args.bootstrap:
                server = await asyncio.start_server(handle_peer, host="0.0.0.0", port=args.port)
                print(f"[P2P] Bootstrap listening on 0.0.0.0:{args.port}")
            else:
                server = None

            # Connect to peers specified via --peer
            if args.peer:
                for peer_addr in args.peer:
                    try:
                        host, port = peer_addr.split(":")
                        await connect_to_peer(host, int(port))
                        print(f"[P2P] Connected to peer {host}:{port}")
                    except Exception as e:
                        print(f"[P2P] Failed to connect to peer {peer_addr}: {e}")

            print(format_message({"type":"notice","text":"Type /quit to exit (P2P mode)"}))

            # Main P2P chat loop: send user input to all peers
            while True:
                text = await asyncio.to_thread(input)
                print("\033[1A\033[2K", end="", flush=True)
                if text.strip() == "/quit":
                    break
                msg = {"type": "msg", "nick": args.nick or "anon", "text": text}
                await broadcast_to_peers(msg)

            # Graceful shutdown
            for (host, port), (reader, writer) in list(peers.items()):
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
            if server:
                server.close()
                await server.wait_closed()

        async def handle_peer(reader, writer):
            # Accept incoming peer connection
            addr = writer.get_extra_info("peername")
            print(f"[P2P] Peer connected from {addr}")
            # Handshake: receive their hello
            data = await reader.readline()
            if not data:
                writer.close()
                await writer.wait_closed()
                return
            obj = json.loads(data.decode("utf-8", errors="replace").rstrip("\n"))
            if obj.get("type") != "hello":
                writer.close()
                await writer.wait_closed()
                return
            peer_nick = obj.get("nick", "anon")
            # Send our hello
            writer.write((json.dumps({"type": "hello", "nick": args.nick or "anon"}) + "\n").encode("utf-8"))
            await writer.drain()
            # Add to peers and start receiving
            peer_addr = addr if addr else ("unknown", 0)
            peers[peer_addr] = (reader, writer)
            asyncio.create_task(peer_recv_loop(reader, peer_addr, peer_nick))

        try:
            asyncio.run(p2p_main())
        except KeyboardInterrupt:
            print("[P2P] Shutting down.")
