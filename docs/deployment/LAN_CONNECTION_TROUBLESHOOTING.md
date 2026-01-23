# Code Scalpel Docker - LAN Device Connection Troubleshooting

**Date:** December 14, 2025  
**Issue:** Connection refused from remote LAN device  
**Status:** Diagnostic guide for multi-device deployments

## Quick Diagnosis

The error `TypeError: fetch failed` when connecting from a LAN device typically means:

1. **Wrong IP address** - Using incorrect host IP
2. **Firewall blocking** - Port 8593 not accessible from network
3. **Port not exposed** - Container not bound to 0.0.0.0
4. **Network routing issue** - Devices not on same network

## Your Current Setup

### Host Machine Information
```
Host IP (ETH0): 172.28.56.173
Docker Bridge: 172.18.0.1, 172.31.0.1, 172.17.0.1
Port Status: LISTENING on 0.0.0.0:8593
Firewall: INACTIVE (no blocking rules)
```

### Problem Identified
You were trying to connect to **172.16.0.5:8593**, but:
- Your host machine is **172.28.56.173**
- That IP (172.16.0.5) is not your host machine
- The connection times out because wrong IP is used

## Solution: Find Your Correct Host IP

### Method 1: From Host Machine (Quick)
```bash
# Find your actual IP address
hostname -I

# Or more detailed
ip addr | grep "inet " | grep -v "127.0.0.1"

# Output should show something like:
# inet 172.28.56.173/20 brd 172.28.63.255 scope global eth0
```

### Method 2: From LAN Device
```bash
# Ping your host machine to see what IP responds
ping hostname-of-your-machine

# Or if you can SSH in
ssh user@your-host
# Then run: hostname -I
```

### Method 3: Check Router/DHCP
1. Log into your WiFi router
2. Look for connected devices
3. Find your host machine and note its IP address

## Connecting from LAN Device - Correct Method

### Step 1: Find Your Host's Actual IP
```bash
# On the Docker host machine:
ip addr | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}'

# Output: 172.28.56.173/20 (or similar)
```

### Step 2: Use Correct IP from LAN Device

**INSTEAD OF:** `http://172.16.0.5:8593`  
**USE:** `http://172.28.56.173:8593` (or your actual host IP)

### Step 3: Test Connection
```bash
# From LAN device:
curl http://172.28.56.173:8593/sse

# Should return:
# HTTP/1.1 200 OK
# content-type: text/event-stream
```

## Verify Docker Container Setup

Make sure your container is started with correct port binding:

```bash
# Check current binding
docker port code-scalpel-mcp

# Should show:
# 8593/tcp -> 0.0.0.0:8593

# If not, restart with correct binding:
docker stop code-scalpel-mcp
docker rm code-scalpel-mcp
docker run -d \
  --name code-scalpel-mcp \
  -p 0.0.0.0:8593:8593 \
  -v $(pwd):/workspace \
  code-scalpel:1.5.3
```

## Common LAN Connection Issues

### Issue 1: Connection Refused (Wrong IP)

**Symptom:**
```
TypeError: fetch failed on http://172.16.0.5:8593/sse
```

**Solution:**
1. Verify your host machine's actual IP:
   ```bash
   hostname -I
   ip addr | grep "inet " | grep eth
   ```

2. Use the correct IP in your client configuration

3. Test with curl:
   ```bash
   # From LAN device
   curl http://YOUR_CORRECT_HOST_IP:8593/sse
   ```

### Issue 2: Connection Timeout (Network Unreachable)

**Symptom:**
```
Error connecting to http://your-host-ip:8593
Connection timeout after 30 seconds
```

**Causes:**
- Host and LAN device not on same network
- Network switch/router not routing between networks
- Firewall blocking on firewall-enabled machine

**Solution:**

1. **Check network connectivity:**
   ```bash
   # From LAN device, ping host
   ping 172.28.56.173
   
   # Should see replies, not "unreachable"
   ```

2. **Enable firewall port if needed:**
   ```bash
   # On host if UFW enabled:
   sudo ufw allow 8593
   sudo ufw allow from 172.16.0.0/24 to any port 8593  # Your LAN subnet
   ```

3. **Check Docker binding:**
   ```bash
   docker port code-scalpel-mcp
   # Must show: 0.0.0.0:8593 (not 127.0.0.1:8593)
   ```

### Issue 3: Connection Refused (Port Not Exposed)

**Symptom:**
```
Error: Connection refused
Port 8593 is not accessible
```

**Solution:**

Verify the container is running with correct port mapping:

```bash
# Check container
docker ps | grep code-scalpel-mcp

# Should show: 0.0.0.0:8593->8593/tcp

# If missing, restart:
docker stop code-scalpel-mcp
docker run -d -p 0.0.0.0:8593:8593 code-scalpel:1.5.3
```

### Issue 4: Firewall Blocking

**Symptom:**
```
Connection refused (no response at all)
Timeout after many seconds
```

**Solution:**

1. **Check if firewall is enabled:**
   ```bash
   sudo ufw status
   # If "Status: active", firewall is on
   ```

2. **Allow port 8593:**
   ```bash
   sudo ufw allow 8593
   sudo ufw allow 8593/tcp
   sudo ufw reload
   ```

3. **Allow specific subnet if needed:**
   ```bash
   # Allow your LAN subnet (e.g., 172.16.0.0/24)
   sudo ufw allow from 172.16.0.0/24 to any port 8593
   ```

4. **Test firewall port:**
   ```bash
   # From LAN device
   curl -v http://HOST_IP:8593/sse
   # -v shows if it can reach the port
   ```

### Issue 5: Network Isolation (Different Subnets)

**Symptom:**
```
Ping works but HTTP fails
```

**Cause:**
- Devices on different network subnets
- Router not routing between networks

**Solution:**

1. **Check if on same network:**
   ```bash
   # On host
   ip addr | grep "inet " | grep eth
   # Shows: 172.28.56.173/20
   
   # On LAN device, check your IP and gateway
   # Should have similar subnet (172.28.x.x in this case)
   ```

2. **If different subnets:**
   - Connect both devices to same WiFi
   - Or configure router to route between networks

## Step-by-Step Connection Guide

### For VS Code on LAN Device

1. **Find host IP:**
   ```bash
   # On host machine:
   hostname -I
   # Example output: 172.28.56.173
   ```

2. **Configure MCP Server:**
   - Host: `172.28.56.173` (your actual IP)
   - Port: `8593`
   - Protocol: HTTP

3. **Test connection:**
   ```bash
   curl http://172.28.56.173:8593/sse
   ```

4. **If successful, configure in VS Code:**
   - Settings → Extensions → Code Scalpel
   - Set MCP Host: `172.28.56.173:8593`
   - Restart extension

### For Claude Desktop on LAN Device

1. **Get host IP:**
   ```bash
   # Run on host
   hostname -I | awk '{print $1}'
   # Note: 172.28.56.173
   ```

2. **Edit `claude_desktop_config.json`:**
   ```json
   {
     "mcpServers": {
       "code-scalpel": {
         "command": "curl",
         "args": ["http://172.28.56.173:8593"]
       }
     }
   }
   ```

3. **Test first:**
   ```bash
   curl http://172.28.56.173:8593/sse
   ```

4. **Restart Claude Desktop**

### For Python Script on LAN Device

```python
import httpx

async def connect_to_scalpel(host_ip="172.28.56.173"):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://{host_ip}:8593/sse",
                timeout=10.0
            )
            print(f"Connected: {response.status_code}")
        except httpx.ConnectError as e:
            print(f"Connection failed: {e}")
            print(f"Check that host IP is correct and port 8593 is open")
```

## Diagnostic Commands (Run from LAN Device)

### Test Network Connectivity

```bash
# 1. Can you reach the host?
ping 172.28.56.173
# Should see: Reply from 172.28.56.173...

# 2. Can you reach the specific port?
curl -v http://172.28.56.173:8593/sse
# Should see: HTTP/1.1 200 OK

# 3. Check DNS if using hostname
nslookup hostname.local
# Or: ping hostname.local
```

### Detailed Connection Test

```bash
# Full verbose test
curl -v --connect-timeout 5 \
  http://172.28.56.173:8593/sse

# Expected successful output:
# * Connected to 172.28.56.173 (172.28.56.173) port 8593 (#0)
# > GET /sse HTTP/1.1
# < HTTP/1.1 200 OK
# < content-type: text/event-stream
```

## Network Setup Best Practices

### For Development (Single Network)

1. **Ensure devices on same WiFi network**
   - Check both connected to same WiFi SSID
   - Get IP from router if unsure

2. **Use static IP on host** (optional but helps)
   ```bash
   # Note down your IP:
   hostname -I
   
   # Configure in router or netplan to keep IP stable
   ```

3. **Start container with port exposed:**
   ```bash
   docker run -d \
     --name code-scalpel-mcp \
     -p 0.0.0.0:8593:8593 \
     -v $(pwd):/workspace \
     code-scalpel:1.5.3
   ```

### For Production (Multiple Networks)

1. **Use static hostname:**
   ```bash
   # Use hostname instead of IP
   # Configure in /etc/hosts or DNS
   # Example: scalpel-server.local
   ```

2. **Use reverse proxy** (optional)
   ```bash
   # nginx, haproxy, or similar
   # Allows using standard port 80 or 443
   ```

3. **Enable authentication** (optional)
   ```bash
   # If exposing to untrusted network
   # Add API key or OAuth authentication
   ```

## Quick Reference

### Wrong IP Used
```bash
# You tried:   http://172.16.0.5:8593
# Should use:  http://172.28.56.173:8593 (your actual host IP)

# Find it with:
hostname -I
```

### Port Not Exposed
```bash
# Check binding:
docker port code-scalpel-mcp

# Should show: 0.0.0.0:8593->8593/tcp

# If 127.0.0.1 only, restart with:
docker run -p 0.0.0.0:8593:8593 code-scalpel:1.5.3
```

### Firewall Blocking
```bash
# Check:
sudo ufw status

# Allow port:
sudo ufw allow 8593
```

### Test from LAN Device
```bash
# First, verify host IP:
# (Run on host) hostname -I

# Then from LAN device:
curl http://HOST_IP:8593/sse

# Should get HTTP 200 with event-stream content
```

## Support

If connection still fails after checking above:

1. **Collect diagnostic info:**
   ```bash
   # On host:
   echo "Host IP:" && hostname -I
   echo "Docker status:" && docker port code-scalpel-mcp
   echo "Firewall:" && sudo ufw status
   echo "Port listening:" && ss -tlnp | grep 8593
   
   # From LAN device:
   echo "Can ping:" && ping -c 1 HOST_IP
   echo "Connection test:" && curl -v http://HOST_IP:8593/sse
   ```

2. **Check container logs:**
   ```bash
   docker logs -f code-scalpel-mcp
   ```

3. **Verify with direct IP test:**
   ```bash
   # Use actual IP, not hostname
   curl http://172.28.56.173:8593/sse
   ```

4. **Check docker-compose if using it:**
   ```bash
   docker-compose ps
   docker-compose logs mcp-server
   ```

---

**Status:** Container configured for LAN access  
**Port:** 0.0.0.0:8593 (exposed to all interfaces)  
**Firewall:** INACTIVE (not blocking)  
**Connection:** Ready for LAN devices
