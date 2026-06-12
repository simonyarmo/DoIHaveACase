import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request

from api.dependencies import get_current_user
from api.routes import auth, cases, chat, health, knowledge
from config import settings
from database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(title="DepositShield API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)

# All Phase 2+ feature routers (cases, documents, timeline, notifications, ...)
# must be included into `protected_router` rather than added to `app` directly,
# so they require authentication by construction instead of by remembering to
# attach `CurrentUserDep` to every new endpoint.
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(knowledge.router)
protected_router.include_router(cases.router)
app.include_router(protected_router)
