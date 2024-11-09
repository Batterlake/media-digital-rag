import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

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
            "text": "Here are some key findings from the documents:\n\n"
            + "1. The search term appears in multiple contexts\n"
            + "2. Several documents contain related information\n"
            + "3. Found some relevant media files\n\n",
            "images": [
                "/static/previews/0_preview.jpg",
                "/static/previews/1_preview.jpg",
                "/static/previews/2_preview.jpg",
                "/static/previews/3_preview.jpg",
                "/static/previews/4_preview.jpg",
                "/static/previews/5_preview.jpg",
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


@router.get("/api/search")
async def search(q: str):
    """Search endpoint that returns streaming results."""
    return StreamingResponse(search_stream(q), media_type="application/x-ndjson")
