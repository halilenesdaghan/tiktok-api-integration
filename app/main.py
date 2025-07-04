# app/main.py

import os
import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.endpoints import auth, tiktok, analytics
from app.config.settings import settings
from app.config.database import init_db


# Logger kurulumu
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
)

# Static files için mount (eğer static dosyalar varsa)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware'ler
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.debug(f"{request.method} {request.url.path} - Completed in {process_time:.4f}s")
    return response

# CORS middleware - ngrok için önemli
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ngrok için tüm origin'lere izin ver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Ngrok ve diğer proxy'ler için
)

# Startup ve Shutdown eventleri
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up TikTok API Integration...")
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization successful.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down TikTok API Integration...")

# API Router'ları
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(tiktok.router, prefix=settings.API_V1_STR + "/tiktok", tags=["TikTok"])
app.include_router(analytics.router, prefix=settings.API_V1_STR + "/analytics", tags=["Analytics"])

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "TikTok API Integration",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Root endpoint - index.html'i serve et
@app.get("/", tags=["Root"])
async def read_root():
    """Ana sayfayı serve et"""
    # Farklı yolları dene
    possible_paths = [
        Path("index.html"),  # Proje root'unda
        Path(__file__).parent.parent / "index.html",  # app klasörünün bir üstü
        Path(__file__).parent.parent.parent / "index.html",  # İki üst klasör
        Path.cwd() / "index.html",  # Current working directory
    ]
    
    for index_path in possible_paths:
        if index_path.exists() and index_path.is_file():
            logger.info(f"Serving index.html from: {index_path}")
            return FileResponse(
                path=str(index_path),
                media_type="text/html",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # Eğer dosya bulunamazsa, embedded HTML döndür
    logger.warning("index.html not found in any expected location")
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TikTok API Integration</title>
    </head>
    <body>
        <h1>TikTok API Integration</h1>
        <p>API is running!</p>
        <p><a href="/docs">API Documentation</a></p>
        <p><a href="/health">Health Check</a></p>
    </body>
    </html>
    """, status_code=200)

# Error handler for debugging
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
    return {
        "error": "Internal Server Error",
        "detail": str(exc) if settings.DEBUG else "An error occurred",
        "type": type(exc).__name__
    }