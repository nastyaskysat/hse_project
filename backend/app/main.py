from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import re
from collections import defaultdict
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import time
import socket
from src.queries.orm import SyncOrm

SyncOrm.create_tables()

app = FastAPI()

# Настройка путей логов
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "access.log"
UPLOAD_LOG_PATH = LOG_DIR / "upload.log"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    log_data = f"{client_ip} - - [{datetime.now().strftime('%d/%b/%Y:%H:%M:%S %z')}] \"{request.method} {request.url.path}\" {response.status_code} 0\n"

    with open(LOG_PATH, "a") as f:
        f.write(log_data)

    try:
        ip_address = SyncOrm.insert_ip_address(client_ip)
        whois_info = get_whois_info(client_ip)

        if whois_info:
            SyncOrm.add_whois_info(
                ip=client_ip,
                asn=whois_info.get('asn'),
                name=whois_info.get('name'),
                country=whois_info.get('country')
            )
    except Exception as e:
        print(f"Ошибка при сохранении WHOIS информации для {client_ip}: {e}")

    return response

templates = Jinja2Templates(directory="templates")

def parse_apache_log(log_path: str) -> Dict[str, Any]:
    pattern = r'(\S+) - - \[(.*?)\] "(.*?)" (\d+) (\d+)'
    daily_stats = defaultdict(int)
    hourly_stats = defaultdict(int)
    ip_stats = defaultdict(int)
    total_visits = 0

    try:
        with open(log_path, 'r') as f:
            for line in f:
                match = re.match(pattern, line)
                if match:
                    ip, date, request, status, size = match.groups()
                    try:
                        date_obj = datetime.strptime(date.split()[0], '%d/%b/%Y:%H:%M:%S')
                        date_key = date_obj.strftime('%Y-%m-%d')
                        hour_key = date_obj.strftime('%H')
                    except:
                        continue

                    daily_stats[date_key] += 1
                    hourly_stats[hour_key] += 1
                    ip_stats[ip] += 1
                    total_visits += 1

        sorted_ips = dict(sorted(ip_stats.items(), key=lambda item: item[1], reverse=True))

        return {
            'daily': dict(sorted(daily_stats.items())),
            'hourly': dict(sorted(hourly_stats.items())),
            'ips': {k: sorted_ips[k] for k in list(sorted_ips)[:20]},
            'total_visits': total_visits,
            'unique_ips': len(ip_stats),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {'error': str(e)}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/logs")
async def get_logs():
    if not LOG_PATH.exists():
        return JSONResponse(content={'error': f'Log file not found at {LOG_PATH}'})
    content = parse_apache_log(str(LOG_PATH))
    return JSONResponse(content=content)

@app.post("/api/upload")
async def upload_log_file(logfile: UploadFile = File(...)):
    try:
        contents = await logfile.read()
        with open(UPLOAD_LOG_PATH, 'wb') as f:
            f.write(contents)
        return {"message": "Log file uploaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")

def whois_query(ip, server, port=43):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server, port))
            s.send(f"{ip}\r\n".encode())
            response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data
        return response.decode()
    except Exception as e:
        print(f"Ошибка при запросе к whois-серверу {server}: {e}")
        return None

def parse_whois_response(response):
    data = {
        "asn": None,
        "name": None,
        "country": None,
    }

    asn_patterns = [
        re.compile(r"origin:\s*([\w-]+)", re.IGNORECASE),
        re.compile(r"OriginAS:\s*([\w-]+)", re.IGNORECASE),
        re.compile(r"aut-num:\s*([\w-]+)", re.IGNORECASE),
    ]
    name_patterns = [
        re.compile(r"netname:\s*([\w-]+)", re.IGNORECASE),
        re.compile(r"NetName:\s*([\w-]+)", re.IGNORECASE),
        re.compile(r"descr:\s*([\w\s-]+)", re.IGNORECASE),
    ]
    country_patterns = [
        re.compile(r"country:\s*([\w-]+)", re.IGNORECASE),
        re.compile(r"Country:\s*([\w-]+)", re.IGNORECASE),
    ]

    for pattern in asn_patterns:
        match = pattern.search(response)
        if match:
            data["asn"] = match.group(1)
            break

    for pattern in name_patterns:
        match = pattern.search(response)
        if match:
            data["name"] = match.group(1)
            break

    for pattern in country_patterns:
        match = pattern.search(response)
        if match:
            data["country"] = match.group(1)
            break

    return data

def get_whois_info(ip):
    whois_servers = [
        "whois.ripe.net",
        "whois.arin.net",
        "whois.apnic.net",
        "whois.radb.net",
        "whois.iana.org",
    ]

    for server in whois_servers:
        response = whois_query(ip, server)
        if response:
            info = parse_whois_response(response)
            if info["asn"] and info["name"] and info["country"]:
                return info
        else:
            print(f"Не удалось получить ответ от сервера {server}.")

    return None

@app.get("/api/get_stats")
async def whois_lookup(ip: str):
    if not ip:
        raise HTTPException(status_code=400, detail="IP-адрес не указан")

    info = get_whois_info(ip)
    if info:
        SyncOrm.add_whois_info(
            ip=ip,
            asn=info.get('asn'),
            name=info.get('name'),
            country=info.get('country')
        )
        return info
    else:
        raise HTTPException(status_code=404, detail="Не удалось получить whois-информацию")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
