from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db
from core.scheduler import scheduler
from api.routes import router as api_router
from api.views import router as views_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    yield
    await scheduler.stop()

app = FastAPI(title="Funding Rate Farming API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(views_router)
