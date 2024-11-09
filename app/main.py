import logging
import logging.config

import yaml
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routers import files, home

# Configure logging
with open("log_conf.yaml") as file:
    config = yaml.safe_load(file)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

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
