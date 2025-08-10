# Server file
from fastapi import FastAPI, Request, HTTPException, Form
from urllib.parse import quote
import httpx
import json
import secrets
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Navigate to /docs to explore available APIs"}

CLIENT_ID = 'CLIENT ID'
SCOPES = 'SCOPES'
REDIRECT_URI = 'REDIRECT_URI'
CLIENT_SECRET = 'CLIENT_SECRET'

@app.post("/integration/connect")
async def authorize_hubspot(user_id: str = Form(...), org_id: str = Form(...)):
    # Take two parameters: user_id and org_id.
    if not user_id.strip() or not org_id.strip():
        return {"error": "user_id and org_id cannot be empty"}

    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    
    # Create and Save an auth state (redis for 6 min).
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    # Create and Return an auth redirect URL
    authUrl = f'https://app.hubspot.com/oauth/authorize?client_id={quote(CLIENT_ID)}&scope={quote(SCOPES)}&redirect_uri={quote(REDIRECT_URI)}&state={quote(encoded_state)}'
    return authUrl

@app.get("/oauth/callback")
async def hubspot_oauth_callback(request: Request):
    # 1. API endpoint to handle HubSpot callback, receive authorization code.
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    encoded_state = request.query_params.get('state')
    if not encoded_state:
        raise HTTPException(status_code=400, detail="Missing state")

    # 2. Extract values from the received state and compare with saved state in Redis;
    state_data = json.loads(encoded_state)
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail="State does not match or is not available in Redis.")

    # 3.Prepare payload and make API call to exchange the authorization code for an access token
    form_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }

    # Getting Access Token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    if response.status_code == 200:
        token_data = response.json()
        # Delete saved state after successful token exchange
        await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
        # Save credentials in Redis (with expiration)
        await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(token_data), expire=600)
        return {"message": "Successfully acquired HubSpot access token."}
    else:
        return {
            "error": "Failed to fetch tokens",
            "status": response.status_code,
            "detail": response.text
        }


async def get_hubspot_credentials(user_id, org_id):
    if not user_id.strip() or not org_id.strip():
        return {"error": "user_id and org_id cannot be empty"}

    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')

    return credentials

@app.post('/integrations/hubspot/credentials')
async def get_hubspot_credentials_integration(user_id: str = Form(...), org_id: str = Form(...)):
    return await get_hubspot_credentials(user_id, org_id)
