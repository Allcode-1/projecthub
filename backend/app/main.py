from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import v1_router
from app.auth.routes import router as auth_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.health import liveness_payload, readiness_payload
from app.core.logging import configure_logging
from app.core.request_logging import register_request_logging

configure_logging()
app = FastAPI()

register_exception_handlers(app)
register_request_logging(app)

app.include_router(auth_router)
app.include_router(v1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck():
    return liveness_payload()


@app.get("/health/live")
def liveness_check():
    return liveness_payload()


@app.get("/health/ready")
def readiness_check():
    payload, status_code = readiness_payload()
    return JSONResponse(status_code=status_code, content=payload)
