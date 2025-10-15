from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version=settings.VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def get_healthcheck() -> dict[str, str]:
    return {"message": "OK"}
