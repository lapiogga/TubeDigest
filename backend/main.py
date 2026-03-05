from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import youtube, auth

from database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="TubeDigest API", version="1.0.0", lifespan=lifespan)
app.include_router(youtube.router)
app.include_router(auth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to TubeDigest API"}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
