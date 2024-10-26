from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api import auth, scraping, configurations, dynamic_endpoints
from app.core.config import settings
from app.db.database import supabase

app = FastAPI(title=settings.PROJECT_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(scraping.router, prefix="/scraping", tags=["scraping"])
app.include_router(configurations.router, prefix="/configurations", tags=["configurations"])
app.include_router(dynamic_endpoints.router, prefix="/dynamic", tags=["dynamic_endpoints"])

@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    return {"message": "Welcome to the Web Scraping Service"}

# Session management
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    response = await call_next(request)
    # Note: This assumes you have implemented session management.
    # If not, you may want to remove or modify this middleware.
    return response
