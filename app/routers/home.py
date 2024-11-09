import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from ..db import colpali_client, vector_search
from ..llm import request_with_images

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(
        "index.html", {"request": request}
    )


def substitute_objects(input_string, objects):
    import re

    def replace_pattern(match):
        index = int(match.group(1)) - 1
        return objects[index] if 0 <= index < len(objects) else ""

    return re.sub(r"@(\d+)@", replace_pattern, input_string)


def unique_dicts(dicts, key1, key2):
    seen = set()
    unique_list = []
    for d in dicts:
        identifier = (d[key1], d[key2])
        if identifier not in seen:
            seen.add(identifier)
            unique_list.append(d)
    return unique_list


async def search_stream(query: str) -> AsyncGenerator[bytes, None]:
    """Generate streaming search results with text and images."""
    try:
        multivector_query = colpali_client.embed_texts([query])[0]
        yield (
            json.dumps({"text": "Generating text embeddings...", "images": []}) + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        # embedding -> database
        top_k = 5
        matches = vector_search(multivector_query, top_k)
        matches = unique_dicts(matches, "file_id", "page_id")
        links_to_matches = [
            f"[{m['file_id'].split('/')[-1]}.pdf](/pdf/{m['file_id'].split('/')[-1]}.pdf#page={m['page_id']})"
            for m in matches
        ]
        yield (
            json.dumps(
                {
                    "text": f"Found top {top_k} pages...",
                    "images": [f"{m['file_id']}/{m['page_id']}.jpg" for m in matches],
                    "links": [
                        [m["file_id"].split("/")[-1], m["page_id"]] for m in matches
                    ],
                }
            )
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        yield (
            json.dumps(
                {
                    "text": substitute_objects(
                        request_with_images(
                            query,
                            [
                                Path(f"{match['file_id']}/{match['page_id']}.jpg")
                                for match in matches
                            ],
                        ),
                        links_to_matches,
                    ),
                    "images": [],
                },
                ensure_ascii=False,
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


async def search_with_image(
    query: str, image_path: Path
) -> AsyncGenerator[bytes, None]:
    """Generate streaming search results with text and images."""
    try:
        multivector_query = colpali_client.embed_texts([query])[0]
        yield (
            json.dumps({"text": "Generating text embeddings...", "images": []}) + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        multivector_image = colpali_client.embed_images([str(image_path)])[0]
        yield (
            json.dumps({"text": "Generating image embeddings...", "images": []}) + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        # embedding -> database
        top_k = 5
        matches_query = vector_search(multivector_query, top_k)
        yield (
            json.dumps(
                {
                    "text": f"Found top {top_k} pages for query...",
                    "images": [],
                }
            )
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        # top-k documents -> llm
        matches_image = vector_search(multivector_image, 5)
        sorted_matches = sorted(
            (matches_query + matches_image), key=lambda x: x["score"], reverse=True
        )
        matches = unique_dicts(sorted_matches, "file_id", "page_id")
        matches = sorted_matches[:top_k]
        links_to_matches = [
            f"[{m['file_id']}.pdf](/pdf/{m['file_id']}.pdf#page={m['page_id']})"
            for m in matches
        ]
        yield (
            json.dumps(
                {
                    "text": f"Found top {top_k} pages for image ...",
                    "images": [
                        f"{m['file_id']}/{m['page_id']}.jpg" for m in matches_image
                    ]
                    + [f"{m['file_id']}/{m['page_id']}.jpg" for m in matches_query],
                    "links": [[m["file_id"], m["page_id"]] for m in matches],
                }
            )
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        yield (
            json.dumps(
                {
                    "text": substitute_objects(
                        request_with_images(
                            query,
                            [
                                Path(f"{match['file_id']}/{match['page_id']}.jpg")
                                for match in matches
                            ],
                        ),
                        links_to_matches,
                    ),
                    "images": [],
                },
                ensure_ascii=False,
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


@router.post("/api/search")
async def search(q: str = Form(...), image: UploadFile = File(None)):
    """Search endpoint that returns streaming results."""
    if image and image.filename:
        # Save uploaded image temporarily
        temp_path = Path("temp_uploads")
        temp_path.mkdir(exist_ok=True)
        image_path = temp_path / image.filename
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        return StreamingResponse(
            search_with_image(q, image_path), media_type="application/x-ndjson"
        )
    return StreamingResponse(search_stream(q), media_type="application/x-ndjson")


# Keep the GET endpoint for backward compatibility
@router.get("/api/search")
async def search_get(q: str):
    """Search endpoint that returns streaming results (GET method)."""
    return StreamingResponse(search_stream(q), media_type="application/x-ndjson")
