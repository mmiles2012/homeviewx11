"""HomeView server entry point."""
from fastapi import FastAPI

from server.config import get_config

app = FastAPI(title="HomeView", version="1.0.0")


@app.get("/api/v1/server/health")
async def health() -> dict[str, str]:
    """Return server health status."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("server.main:app", host=config.host, port=config.port, reload=False)
