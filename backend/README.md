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

## 🔗 Access API Docs

Once the server is running, open your browser and go to:

```
http://localhost:8000/docs
```

This opens the interactive API documentation powered by **Swagger UI**.

---

## 🧠 Step 2: Add Redis to the Project

### ✅ Prerequisites

* Redis is installed on your local machine and running before starting the project.

---

### 1. Install Redis and Kombu

Use either of the following commands:

```bash
pip install redis kombu
```

Or (using Python launcher):

```bash
py -m pip install redis kombu
```

---

### 2. Create a Redis Configuration File in the Project Root (`redis_client.py`)

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