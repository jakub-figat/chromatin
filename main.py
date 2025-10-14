from fastapi import FastAPI


app = FastAPI()


@app.get("/health")
async def get_healthcheck() -> dict[str, str]:
    return {"message": "OK"}
