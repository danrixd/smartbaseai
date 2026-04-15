from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import routes_chat, routes_admin, routes_auth, routes_files
from .logging_config import RequestIdMiddleware, configure_logging

configure_logging()

app = FastAPI(title="SmartBase API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)

app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_admin.router)
app.include_router(routes_files.router)
