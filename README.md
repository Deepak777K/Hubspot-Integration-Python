# HubSpot Integration — FastAPI Server

---

## Step 1: Set Up FastAPI Server

### Prerequisites

* Python 3.7 or higher installed

---

### 1.1 Install FastAPI and Uvicorn

Use either of the following commands:

```bash
pip install fastapi uvicorn
```

Or (if using Python launcher):

```bash
py -m pip install fastapi uvicorn
```

---

### 1.2. Create a Server File (`main.py`)

Add the following code:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from FastAPI!"}
```

---

### 1.3. Run the FastAPI App

If your file is named `main.py`, use:

```bash
uvicorn main:app --reload
```

Or (using Python launcher):

```bash
py -m uvicorn main:app --reload
```

---

## Access API Docs

Once the server is running, open your browser and go to:

```
http://localhost:8000/docs
```

This opens the interactive API documentation powered by **Swagger UI**.

---

## Step 2: Add Redis to the Project

### ✅ Prerequisites

* Redis is installed on your local machine and running before starting the project.

---

### 2.1. Install Redis and Kombu

Use either of the following commands:

```bash
pip install redis kombu
```

Or (using Python launcher):

```bash
py -m pip install redis kombu
```

---

### 2.2. Create a Redis Configuration File in the Project Root (`redis_client.py`)

Add the following code:

```python
import os
import redis.asyncio as redis
from kombu.utils.url import safequote

redis_host = safequote(os.environ.get('REDIS_HOST', 'localhost'))
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

async def add_key_value_redis(key, value, expire=None):
    await redis_client.set(key, value)
    if expire:
        await redis_client.expire(key, expire)

async def get_value_redis(key):
    return await redis_client.get(key)

async def delete_key_redis(key):
    await redis_client.delete(key)
```

---

## Step 3: Create HubSpot Integration API Endpoints

This step covers adding **three endpoints** to your FastAPI project for HubSpot OAuth integration.

#### Endpoints Overview

1. **Authorization URL Generation**
2. **OAuth Callback Handler**
3. **Get Saved HubSpot Credentials**

---

#### ✅ Install `httpx`

We will use `httpx` for making async HTTP requests.

```bash
pip install httpx
```

Or (using Python launcher):

```bash
py -m pip install httpx
```

---

### Endpoint 1: Generate HubSpot Authorization URL

#### 📄 Description

This endpoint takes `user_id` and `org_id` as parameters, generates a unique `state` token, stores it in Redis, and returns a HubSpot OAuth 2.0 authorization URL.

#### 📍 Route: `POST /integration/connect`

```python
from fastapi import FastAPI, Request, HTTPException, Form
from urllib.parse import quote
import httpx
import json
import secrets
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

app = FastAPI()

# Replace with your actual credentials
CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
SCOPES = 'auth'
REDIRECT_URI = 'http://localhost:8000/oauth/callback'

@app.post("/integration/connect")
async def authorize_hubspot(user_id: str = Form(...), org_id: str = Form(...)):
    if not user_id.strip() or not org_id.strip():
        return {"error": "user_id and org_id cannot be empty"}

    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }

    encoded_state = json.dumps(state_data)

    # Save state in Redis for 6 minutes
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    auth_url = (
        f'https://app.hubspot.com/oauth/authorize'
        f'?client_id={quote(CLIENT_ID)}'
        f'&scope={quote(SCOPES)}'
        f'&redirect_uri={quote(REDIRECT_URI)}'
        f'&state={quote(encoded_state)}'
    )
    return {"authorization_url": auth_url}
```

---

### Endpoint 2: HubSpot OAuth Callback

#### 📄 Description

This endpoint handles the redirect from HubSpot, receives the authorization `code`, verifies the `state`, and exchanges the code for an access token.

#### 📍 Route: `GET /oauth/callback`

```python
@app.get("/oauth/callback")
async def hubspot_oauth_callback(request: Request):
    # 1. Get code and state from query params
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    encoded_state = request.query_params.get('state')
    if not encoded_state:
        raise HTTPException(status_code=400, detail="Missing state")

    # 2. Parse and validate state
    state_data = json.loads(encoded_state)
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail="Invalid or expired state token")

    # 3. Exchange code for access token
    form_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    if response.status_code == 200:
        token_data = response.json()

        # Clean up state from Redis
        await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')

        # Save token data in Redis (6 minutes)
        await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(token_data), expire=600)

        return {"message": "Successfully acquired HubSpot access token."}
    else:
        return {
            "error": "Failed to fetch tokens",
            "status": response.status_code,
            "detail": response.text
        }
```

---

### Endpoint 3: Retrieve Saved HubSpot Credentials

#### 📄 Description

This endpoint takes `user_id` and `org_id` and returns the access token and other OAuth credentials from Redis.

#### 📍 Helper Function

```python
async def get_hubspot_credentials(user_id: str, org_id: str):
    if not user_id.strip() or not org_id.strip():
        return {"error": "user_id and org_id cannot be empty"}

    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials found.")

    return json.loads(credentials)
```

---

#### 📍 Route: `POST /integrations/hubspot/credentials`

```python
@app.post("/integrations/hubspot/credentials")
async def get_hubspot_credentials_integration(user_id: str = Form(...), org_id: str = Form(...)):
    return await get_hubspot_credentials(user_id, org_id)
```

---

### ✅ Summary

| Endpoint                            | Method | Description                                    |
| ----------------------------------- | ------ | ---------------------------------------------- |
| `/integration/connect`              | POST   | Generates HubSpot auth URL                     |
| `/oauth/callback`                   | GET    | Handles HubSpot OAuth callback and saves token |
| `/integrations/hubspot/credentials` | POST   | Returns stored credentials for a user/org      |

---
