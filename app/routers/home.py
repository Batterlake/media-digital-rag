import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

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
    # Simulate a streaming response
    chunks = [
        {"text": "Searching through documents...\n", "images": []},
        {"text": f"Found some relevant information about '{query}':\n\n", "images": []},
        {
            "text": request_with_image(query, Path("previews/5/0.jpg")),
            "images": [
                "/previews/0/0.jpg",
                "/previews/1/0.jpg",
                "/previews/2/0.jpg",
                "/previews/3/0.jpg",
                "/previews/4/0.jpg",
                "/previews/5/0.jpg",
            ],
        },
        {
            "text": "Analysis complete. Let me know if you need more specific information.\n",
            "images": [],
        },
    ]

    for chunk in chunks:
        # Convert chunk to JSON and encode as bytes
        yield (json.dumps(chunk) + "\n").encode("utf-8")
        # Add a small delay to simulate processing
        await asyncio.sleep(0.5)


# post (q, image)
@router.get("/api/search")
async def search(q: str):
    """Search endpoint that returns streaming results."""

    # query -> embedder
    multivector_query = colpali_client.embed_texts([q])[0]
    # embedding -> database
    matches = vector_search(multivector_query, 10)
    match = matches[0]
    # top-1 documents -> llm
    return JSONResponse(
        {
            "text": request_with_image(
                q, Path(f"{match['file_id']}/{match['page_id']}.jpg")
            ),
            "images": [f"{m['file_id']}/{m['page_id']}.jpg" for m in matches],
        }
    )
    # return StreamingResponse(search_stream(q), media_type="application/x-ndjson")
