import os
import dns.resolver
import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Dynamic DNS Controller")
templates = Jinja2Templates(directory="app")

DUCKDNS_TOKEN = os.getenv("DUCKDNS_TOKEN", "")
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "target-ddns")

def get_current_dns_ip(domain: str) -> str:
    custom_resolver = dns.resolver.Resolver()

    custom_resolver.nameservers = [
        '1.1.1.1',  # Cloudflare DNS
        '8.8.8.8',  # Google DNS
    ]

    custom_resolver.timeout = 2.0
    custom_resolver.lifetime = 2.0

    try:
        full_domain = f"{domain}.duckdns.org"
        answers = dns.custom_resolver.resolve(full_domain, 'A')
        return answers[0].to_text()
    except Exception as e:
        return f"Error resolving DNS for {domain}: {e}"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    current_ip = get_current_dns_ip(TARGET_DOMAIN)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "target_domain": TARGET_DOMAIN, "current_ip": current_ip, "message": None}
    )

@app.post("/v1/sync", response_class=HTMLResponse)
async def sync_dns(request: Request, new_ip: str = Form(...)):
    url = f"https://www.duckdns.org/update?domains={TARGET_DOMAIN}&token={DUCKDNS_TOKEN}&ip={new_ip}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        
    status_msg = "IP updated successfully." if "OK" in resp.text else "Failed to update"
    resolved_ip = get_current_dns_ip(TARGET_DOMAIN)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "target_domain": TARGET_DOMAIN,
            "current_ip": resolved_ip,
            "message": f"{status_msg}: {new_ip}"
        }
    )