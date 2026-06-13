# Neo4j Aura Password Reset Guide

## The Problem

Your backend Docker container is getting an **authentication error**:
```
AuthError: The client is unauthorized due to authentication failure
```

**Why?** The password in your `.env` file doesn't match your current Neo4j Aura instance password.

## Quick Fix (2 minutes)

### Step 1: Reset Password in Aura Console

1. Go to: **https://console.neo4j.io**
2. Click on your instance: **HIVE** (ID: `7477e481`)
3. Navigate to: **Details** → **Security** → **Reset password**
4. Click **Reset password** button
5. Copy the new password (you'll only see it once!)

### Step 2: Update `.env`

Edit `ReLived/.env` and replace the password:

```env
# Before (OLD - doesn't work):
NEO4J_HOSTED_PASSWORD=HKVZqYf7cRnFypJPP8I3IABoDBcIbYPV17WZZmfTM3o

# After (NEW - from Aura console):
NEO4J_HOSTED_PASSWORD=<paste-new-password-here>
```

### Step 3: Restart Backend

```bash
# Stop the running container
docker-compose down

# Start it again (will use updated .env)
docker-compose up -d

# Check logs for success
docker-compose logs -f backend_api
```

You should see:
```
✓ Orchestrator initialized and connected to Neo4j
```

## Verify It Works

```bash
# Test the backend is responsive
curl http://localhost:8000/health

# Should return: {"status":"ok"}
```

## Why Did This Happen?

Your `.env` file had an older password that no longer matches your Aura instance. This can happen if:

- ✅ Aura auto-rotated the password for security
- ✅ You manually reset it and forgot to update `.env`
- ✅ You're using a different Aura instance than before

## Prevention

**Always update `.env` immediately after resetting an Aura password**, then restart Docker:

```bash
# Update .env with new password, then:
docker-compose down && docker-compose up -d
```

## Still Having Issues?

### 1. Double-check the password

- Did you copy it correctly from Aura console?
- No extra spaces or quotes?
- Valid characters (base64-ish string)?

### 2. Verify .env is loaded

```bash
# Check what the backend sees
docker-compose logs backend_api | grep "Connection:"
```

Should show your Aura URI.

### 3. Test credentials manually

```bash
cd backend
python3 -c "
from neo4j import AsyncGraphDatabase
import asyncio, os
from dotenv import load_dotenv
load_dotenv('../.env')

async def test():
    driver = AsyncGraphDatabase.driver(
        os.getenv('NEO4J_HOSTED_URI'),
        auth=(os.getenv('NEO4J_HOSTED_USERNAME', 'neo4j'), os.getenv('NEO4J_HOSTED_PASSWORD'))
    )
    async with driver.session() as s:
        r = await s.run('RETURN 1')
        print('✅ Auth OK:', await r.data())
    await driver.close()

asyncio.run(test())
"
```

### 4. Check Aura instance status

Go to https://console.neo4j.io and verify:
- ✅ Instance is **Running** (not Stopped or Paused)
- ✅ No maintenance is in progress
- ✅ You can browse the database (Neo4j Browser button works)

---

**Need help?** Check the backend logs:
```bash
docker-compose logs backend_api -f
```

The new error messages will clearly tell you what's wrong!
