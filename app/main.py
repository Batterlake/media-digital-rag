import logging
import logging.config

import yaml
from fastapi import FastAPI
from fastapi.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

with open("log_conf.yaml") as file:
    config = yaml.safe_load(file)
    logging.config.dictConfig(config)

app = FastAPI(
    middleware=[
        Middleware(SessionMiddleware, secret_key="blah-blah-blah"),
    ],
)
