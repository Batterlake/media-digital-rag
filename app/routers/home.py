import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from ..db import colpali_client, vector_search
from ..llm import request_with_image

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(
        "index.html", {"request": request}
    )


async def search_stream(query: str) -> AsyncGenerator[bytes, None]:
    """Generate streaming search results with text and images."""
    try:
        multivector_query = colpali_client.embed_texts([query])[0]
        yield (
            json.dumps({"text": "Generating text embeddings...", "images": []}) + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        # embedding -> database
        matches = vector_search(multivector_query, 10)
        yield (
            json.dumps(
                {
                    "text": "Found top 10 pages...",
                    "images": [f"{m['file_id']}/{m['page_id']}.jpg" for m in matches],
                }
            )
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        match = matches[0]
        yield (
            json.dumps(
                {
                    "text": request_with_image(
                        query, Path(f"{match['file_id']}/{match['page_id']}.jpg")
                    ),
                    "images": [],
                }
            )
            + "\n"
        ).encode("utf-8")
    except Exception as exc:
        logging.error(exc)
        yield (
            json.dumps(
                {
                    "text": "Не получилось обработать запрос",
                    "images": [],
                }
            )
            + "\n"
        ).encode("utf-8")


# post (q, image)
@router.get("/api/search")
async def search(q: str):
    """Search endpoint that returns streaming results."""
    return StreamingResponse(search_stream(q), media_type="application/x-ndjson")
