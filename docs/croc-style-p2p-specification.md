# Croc-Style P2P Discovery System for Sandpiper

## Architecture Overview

### Components
1. **Discovery Relay Server** - Lightweight coordination service (runs on ThinkPad + ngrok)
2. **Enhanced Client** - P2P-capable chat client with fallback to server mode
3. **Room Code System** - Human-friendly pairing codes like "pine-ocean-42"
4. **Connection Broker** - Helps peers find and connect to each other

### System Flow
```mermaid
sequenceDiagram
    participant A as Alice
    participant R as Discovery Relay
    participant B as Bob
    participant S as Fallback Server
    
    A->>R: create_room() -> "pine-ocean-42"
    A->>A: Start listening on local port
    A->>R: register_peer(code, host, port)
    
    B->>R: lookup_room("pine-ocean-42")
    R->>B: peer_info(alice_host, alice_port)
    
    B->>A: Direct P2P connection attempt
    alt P2P Success
        A<->B: Direct encrypted chat
    else P2P Failed
        A->>S: Fallback to server mode
        B->>S: Fallback to server mode
        A<->S<->B: Server-relayed chat
    end
```

## Discovery Relay Server Implementation

### Core Features
- **Room Code Registry**: Maps codes to peer connection info
- **Peer Coordination**: Helps clients find each other
- **Minimal State**: Only temporary room mappings, no message storage
- **Multi-room Support**: Multiple chat rooms simultaneously
- **Auto-cleanup**: Remove expired/inactive rooms

### Protocol Specification

#### Room Creation
```json
// Client -> Relay
{
  "type": "create_room",
  "nick": "alice",
  "listen_port": 6001
}

// Relay -> Client
{
  "type": "room_created",
  "code": "pine-ocean-42",
  "expires_at": 1735812345
}
```

#### Room Registration
```json
// Client -> Relay  
{
  "type": "register_peer",
  "code": "pine-ocean-42",
  "nick": "alice",
  "host": "192.168.1.100",  // Client's external IP
  "port": 6001
}

// Relay -> Client
{
  "type": "peer_registered",
  "success": true
}
```

#### Room Lookup
```json
// Client -> Relay
{
  "type": "lookup_room",
  "code": "pine-ocean-42",
  "nick": "bob"
}

// Relay -> Client
{
  "type": "room_info",
  "code": "pine-ocean-42",
  "peers": [
    {"nick": "alice", "host": "192.168.1.100", "port": 6001}
  ]
}
```

#### Peer Updates
```json
// Relay -> All room peers (when new peer joins)
{
  "type": "peer_joined",
  "code": "pine-ocean-42", 
  "peer": {"nick": "bob", "host": "192.168.1.101", "port": 6002}
}

// Relay -> All room peers (when peer leaves)
{
  "type": "peer_left",
  "code": "pine-ocean-42",
  "nick": "bob"
}
```

### Room Code Generation
```python
# Word lists for human-friendly codes
ADJECTIVES = ["bright", "swift", "quiet", "bold", "calm", "wild", "free", ...]
NOUNS = ["river", "mountain", "forest", "ocean", "storm", "dawn", ...]

def generate_room_code():
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS) 
    num = random.randint(10, 99)
    return f"{adj}-{noun}-{num}"
```

### Data Structures
```python
# Room registry
rooms = {
    "pine-ocean-42": {
        "created_at": 1735812345,
        "expires_at": 1735898745,  # 24 hours later
        "peers": {
            "alice": {"host": "192.168.1.100", "port": 6001},
            "bob": {"host": "192.168.1.101", "port": 6002}
        }
    }
}
```

## Enhanced Client Implementation

### P2P Mode Arguments
```bash
# Create a new room
sandpiper create --nick alice

# Join existing room
sandpiper join pine-ocean-42 --nick bob

# Traditional server mode (fallback)
sandpiper server --host 192.168.1.10 --port 5000 --nick alice
```

### Client Architecture
```python
class SandpiperClient:
    def __init__(self):
        self.mode = None  # 'p2p' or 'server'
        self.room_code = None
        self.nick = None
        self.relay_host = "relay.example.com"  # Your ngrok endpoint
        self.relay_port = 8000
        
        # P2P specific
        self.listen_port = None
        self.peers = {}  # nick -> connection info
        self.peer_connections = {}  # nick -> (reader, writer)
        
        # Server mode fallback
        self.server_host = None
        self.server_port = None
```

### P2P Connection Management
```python
async def start_p2p_mode(self, room_code, nick):
    # 1. Start listening for peer connections
    self.listen_port = await self.find_free_port()
    await self.start_peer_listener()
    
    # 2. Connect to discovery relay
    await self.connect_to_relay()
    
    # 3. Join/create room
    if room_code:
        await self.join_room(room_code, nick)
    else:
        room_code = await self.create_room(nick)
        print(f"Room created: {room_code}")
        
    # 4. Handle peer connections
    await self.handle_p2p_chat()

async def handle_peer_connection(self, reader, writer):
    # Handle incoming peer connections
    # Authenticate, exchange nick info
    # Add to peer_connections registry
    pass

async def connect_to_peer(self, peer_info):
    # Make outgoing connection to discovered peer
    # Add to peer_connections registry
    pass

async def broadcast_to_peers(self, message):
    # Send message to all connected peers
    # Handle connection failures gracefully
    pass
```

### Fallback Strategy
```python
async def attempt_p2p_connection(self, peer_info, timeout=10):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer_info['host'], peer_info['port']),
            timeout=timeout
        )
        return reader, writer
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None, None

async def fallback_to_server_mode(self):
    print("P2P connection failed. Switching to server mode...")
    await self.disconnect_from_relay()
    await self.start_server_mode(self.server_host, self.server_port, self.nick)
```

## NAT Traversal & Connection Strategy

### Connection Attempt Sequence
1. **Direct Connection**: Try connecting to peer's reported IP/port
2. **Local Network**: Try peer's local IP if on same subnet  
3. **Port Prediction**: Try common port ranges around reported port
4. **Relay Assistance**: Use discovery relay for hole-punching coordination
5. **Server Fallback**: Switch to traditional server mode

### Hole-Punching Protocol
```json
// Relay coordinates simultaneous connection attempts
{
  "type": "coordinate_connection",
  "peers": ["alice", "bob"],
  "timestamp": 1735812345  // Both connect at exact same time
}
```

## Security Considerations

### End-to-End Encryption
```python
# Use Python's cryptography library for E2E encryption
from cryptography.fernet import Fernet

# Each room gets a shared key (derived from room code + password)
def derive_room_key(room_code, password=""):
    return Fernet.generate_key()  # In practice, use PBKDF2

# Encrypt all P2P messages
def encrypt_message(message, key):
    f = Fernet(key)
    return f.encrypt(message.encode()).decode()
```

### Room Password Protection
```json
// Optional room passwords
{
  "type": "create_room", 
  "nick": "alice",
  "password": "secret123"  // Optional
}

{
  "type": "lookup_room",
  "code": "pine-ocean-42",
  "password": "secret123"  // Required if room has password
}
```

## Deployment Configuration

### ThinkPad Discovery Relay Setup
```bash
# Start relay on ThinkPad
cd sandpiper
python3 relay/discovery_relay.py --host 0.0.0.0 --port 8000

# Start ngrok tunnel
ngrok tcp 8000
# Note the ngrok endpoint: tcp://2.tcp.ngrok.io:12345
```

### Client Configuration
```python
# Default relay endpoints (configurable)
DEFAULT_RELAY_ENDPOINTS = [
    "2.tcp.ngrok.io:12345",  # Your ThinkPad relay
    "relay1.sandpiper.chat:8000",  # Community relay (future)
    "relay2.sandpiper.chat:8000"   # Backup relay (future)
]
```

## Testing Strategy

### Local Testing
```bash
# Terminal 1: Discovery relay
python3 relay/discovery_relay.py --host localhost --port 8000

# Terminal 2: Create room
python3 client/client.py create --nick alice --relay localhost:8000

# Terminal 3: Join room  
python3 client/client.py join pine-ocean-42 --nick bob --relay localhost:8000
```

### ngrok Testing
```bash
# ThinkPad: Start relay + ngrok
python3 relay/discovery_relay.py --host 0.0.0.0 --port 8000
ngrok tcp 8000

# Remote machine: Use ngrok endpoint
python3 client/client.py create --nick alice --relay 2.tcp.ngrok.io:12345
```

## File Structure
```
sandpiper/
├── relay/
│   ├── discovery_relay.py      # Main relay server
│   ├── room_manager.py         # Room code generation & management
│   └── nat_helper.py           # NAT traversal coordination
├── client/
│   ├── client.py               # Enhanced client with P2P support
│   ├── p2p_manager.py          # P2P connection management
│   └── crypto_utils.py         # Encryption utilities
├── server/
│   └── server.py               # Original server (fallback mode)
└── docs/
    ├── p2p-usage.md            # User guide
    └── relay-deployment.md     # ThinkPad setup guide
```

## Implementation Phases

### Phase 1: Basic Discovery Relay
- [x] Room code generation system
- [ ] Discovery relay server with room registry
- [ ] Basic room create/join/lookup protocol
- [ ] Client connection to relay

### Phase 2: P2P Connections
- [ ] Client peer listener setup
- [ ] Direct peer connection attempts
- [ ] P2P message broadcasting
- [ ] Connection failure handling

### Phase 3: Robustness & Fallback
- [ ] NAT traversal attempts
- [ ] Automatic server mode fallback
- [ ] Connection retry logic
- [ ] Graceful error handling

### Phase 4: Security & Polish
- [ ] End-to-end encryption
- [ ] Room password protection
- [ ] CLI interface unification
- [ ] Documentation and examples

This specification provides the complete technical foundation for implementing the croc-style P2P discovery system while leveraging your existing ThinkPad + ngrok infrastructure.