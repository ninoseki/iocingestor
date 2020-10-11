from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from iocingestor import __version__
from iocingestor.extras.api import router


def create_app() -> FastAPI:
    app = FastAPI(title="IOC Ingestor", version=__version__)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    print("usage: uvicorn iocingestor.extras.webapp:app")
