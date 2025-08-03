from fastapi import FastAPI

from . import routes_chat, routes_admin, routes_auth, routes_files

app = FastAPI(title="SmartBase API")

app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_admin.router)
app.include_router(routes_files.router)
