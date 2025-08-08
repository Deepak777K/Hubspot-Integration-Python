# Server file
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
import httpx
import json

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request
    })

CLIENT_ID = 'CLIENT ID'
SCOPES = 'SCOPES'
REDIRECT_URI = 'REDIRECT_URI'
STATE = 'STATE'
CLIENT_SECRET = 'CLIENT_SECRET'

@app.get("/integration/connect")
async def authorize_hubspot():
    authUrl = f'https://app.hubspot.com/oauth/authorize?client_id={quote(CLIENT_ID)}&scope={quote(SCOPES)}&redirect_uri={quote(REDIRECT_URI)}&state={quote(STATE)}'
    return RedirectResponse(url=authUrl)

@app.get("/oauth/callback")
async def hubspot_oauth_callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        return {"error": "Missing authorization code"}

    form_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/oauth/callback",
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
        print("Hubspot Access Token Data:", token_data)
        return {"message": "Successfully acquired HubSpot access token."}
    else:
        return {
            "error": "Failed to fetch tokens",
            "status": response.status_code,
            "detail": response.text
        }
