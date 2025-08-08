# Server file
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote

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

@app.get("/integration/connect")
async def authorize_hubspot():
    authUrl = f'https://app.hubspot.com/oauth/authorize?client_id={quote(CLIENT_ID)}&scope={quote(SCOPES)}&redirect_uri=${quote(REDIRECT_URI)}&state={quote(STATE)}'
    return RedirectResponse(url=authUrl)
