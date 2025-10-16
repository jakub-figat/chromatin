from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from common.routes import router as auth_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Include auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
