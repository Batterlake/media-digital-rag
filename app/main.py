import logging
import logging.config
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from qdrant_client import QdrantClient
from qdrant_client.http import models
from starlette.middleware.sessions import SessionMiddleware

from app.routers import files, home

COLLECTION_NAME = "test-collection"
# Configure logging
with open("log_conf.yaml") as file:
    config = yaml.safe_load(file)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)


def get_qdrant_client():
    return QdrantClient(
        url="http://ml.n19:6333",
        api_key="",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    qdrant_client = get_qdrant_client()
    collection_name = COLLECTION_NAME
    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            on_disk_payload=True,  # store the payload on disk
            vectors_config=models.VectorParams(
                size=128,
                distance=models.Distance.COSINE,
                on_disk=True,  # move original vectors to disk
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                quantization_config=models.BinaryQuantization(
                    binary=models.BinaryQuantizationConfig(
                        always_ram=True  # keep only quantized vectors in RAM
                    ),
                ),
            ),
        )
    yield


# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Application",
    description="A modern FastAPI application with automatic API documentation",
    version="1.0.0",
    middleware=[
        Middleware(SessionMiddleware, secret_key="blah-blah-blah"),
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads/"), name="uploads")
app.mount("/previews", StaticFiles(directory="previews/"), name="previews")

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Make templates available to routers
app.state.templates = templates

app.include_router(home.router)
app.include_router(files.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
