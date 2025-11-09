"""FastAPI application initialization."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.logging_config import get_logger, setup_logging
from config.settings import settings
from database.connection import Database
from database.indexes import create_indexes
from api.middleware import RateLimitMiddleware
from api.routes import books, changes

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info("Starting API server")

    # Connect to database
    await Database.connect()
    db = Database.get_database()

    # Create indexes
    await create_indexes(db)

    logger.info("API server started")

    yield

    # Shutdown
    await Database.disconnect()
    logger.info("API server stopped")


app = FastAPI(
    title="Books Crawler API",
    version="1.0.0",
    description="RESTful API for book crawling and monitoring",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Register routers
app.include_router(books.router)
app.include_router(changes.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time
        }
    )

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_health = await Database.health_check()
    status = "healthy" if db_health.get("healthy") else "unhealthy"
    response = {"status": status, "database": db_health}
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

