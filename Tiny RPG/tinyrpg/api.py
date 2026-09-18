"""Tiny RPG FastAPI application assembly."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tinyrpg.config import settings
from tinyrpg.routers.admin import router as admin_router
from tinyrpg.routers.auth import router as auth_router
from tinyrpg.routers.characters import router as characters_router
from tinyrpg.routers.inventory import router as inventory_router
from tinyrpg.routers.users import router as users_router
from tinyrpg.services.rate_limiting import login_rate_limiter

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=[
        "X-Next-Cursor",
        "X-Verification-Token",
        "X-Password-Reset-Token",
    ],
)


@app.get("/")
def welcome_to_tiny_rpg() -> dict[str, str]:
    return {"message": "Welcome to TinyRPG"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(characters_router)
app.include_router(inventory_router)

__all__ = ["app", "login_rate_limiter"]
