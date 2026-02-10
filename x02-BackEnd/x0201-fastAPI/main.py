"""
xMixing FastAPI Backend
=======================
Main API entry point for the xMixing batch control system.

This file sets up the FastAPI application and includes all routers.
All endpoint implementations are in the routers/ directory.

Routers:
- auth_router: /auth/* (login, register)
- users_router: /users/* (user CRUD)
- ingredients_router: /ingredients/*, /ingredient-intake-lists/*
- skus_router: /skus/*, /sku-steps/*, /sku-actions/*, etc.
- production_router: /production-plans/*, /production-batches/*
- plants_router: /plants/*
- monitoring_router: /server-status/*
- views_router: /api/v_* (database views)

Author: xDev
Version: 1.0.0
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine

# Import routers
from routers import (
    auth_router,
    users_router,
    ingredients_router,
    skus_router,
    production_router,
    plants_router,
    monitoring_router,
    views_router,
    warehouses_router
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="xMixing API",
    description="Backend API for xMixing batch control system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = (
    allowed_origins_env.split(",") 
    if allowed_origins_env 
    else ["http://localhost:3000", "http://127.0.0.1:3000", "*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# =============================================================================
# ROUTERS
# =============================================================================

# Include all routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ingredients_router)
app.include_router(skus_router)
app.include_router(production_router)
app.include_router(plants_router)
app.include_router(monitoring_router)
app.include_router(views_router)
app.include_router(warehouses_router)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/", tags=["Health"])
def read_root():
    """Health check endpoint."""
    return {
        "message": "xMixing API",
        "status": "connected",
        "version": "1.0.0"
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
