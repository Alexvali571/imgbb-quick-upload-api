import os
import time
from collections import defaultdict, deque
from typing import Deque

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
MAX_FILE_SIZE = 32 * 1024 * 1024
ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/avif",
}
RATE_LIMIT = 8
RATE_WINDOW_SECONDS = 60

app = FastAPI(
    title="ImgBB Quick Upload API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# Extensia Chrome va apela API-ul dintr-un origin chrome-extension://...
# Nu folosim cookies sau autentificare prin browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_requests: dict[str, Deque[float]] = defaultdict(deque)


def check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    recent = _requests[client_ip]

    while recent and now - recent[0] > RATE_WINDOW_SECONDS:
        recent.popleft()

    if len(recent) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Ai atins limita temporară. Încearcă din nou peste un minut.",
        )

    recent.append(now)


@app.get("/")
async def root():
    return {
        "service": "ImgBB Quick Upload API",
        "status": "online",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "api_key_configured": bool(IMGBB_API_KEY)}


@app.post("/upload")
async def upload_image(request: Request, image: UploadFile = File(...)):
    if not IMGBB_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Serverul nu este configurat cu cheia API ImgBB.",
        )

    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Format neacceptat. Folosește JPG, PNG, GIF, WEBP, BMP, TIFF sau AVIF.",
        )

    content = await image.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Fișierul este gol.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Imaginea depășește limita de 32 MB.")

    filename = image.filename or "image"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as client:
            response = await client.post(
                IMGBB_UPLOAD_URL,
                data={"key": IMGBB_API_KEY},
                files={"image": (filename, content, content_type)},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ImgBB nu a răspuns la timp.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Nu s-a putut contacta ImgBB.")

    try:
        result = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="ImgBB a returnat un răspuns invalid.")

    if not response.is_success or not result.get("success"):
        error = result.get("error") or {}
        message = error.get("message") or result.get("status_txt") or "Încărcarea pe ImgBB a eșuat."
        raise HTTPException(status_code=502, detail=str(message))

    url = (result.get("data") or {}).get("url")
    if not url:
        raise HTTPException(status_code=502, detail="ImgBB nu a returnat linkul imaginii.")

    # Păstrăm formatul de răspuns folosit de extensie.
    return {"success": True, "data": {"url": url}}
