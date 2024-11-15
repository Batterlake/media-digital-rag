import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import numpy as np
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image

from ..db import VectorSearchResult, colpali_client, vector_search
from ..llm import request_with_images

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(
        "index.html", {"request": request}
    )


@router.get("/chat-with-image", response_class=HTMLResponse)
async def chat_with_image(request: Request):
    return request.app.state.templates.TemplateResponse(
        "chat_with_image.html", {"request": request}
    )


def substitute_objects(input_string, objects):
    import re

    def replace_pattern(match):
        index = int(match.group(1)) - 1
        return objects[index] if 0 <= index < len(objects) else ""

    return re.sub(r"@(\d+)@", replace_pattern, input_string)


def unique_dicts(dicts: list[VectorSearchResult]):
    seen = set()
    unique_list = []
    for d in dicts:
        identifier = (d.file_id, d.page_id)
        if identifier not in seen:
            seen.add(identifier)
            unique_list.append(d)
    return unique_list


async def search_with_image(
    query: str, image_path: Path | None = None
) -> AsyncGenerator[bytes, None]:
    """Generate streaming search results with text and images."""
    try:
        multivector_query = await run_in_threadpool(colpali_client.embed_texts, [query])
        multivector_query = multivector_query[0]
        yield (
            json.dumps({"text": "Обработка текстовых представлений...", "images": []})
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        if image_path:
            multivector_image = await run_in_threadpool(
                colpali_client.embed_images, [str(image_path)]
            )
            multivector_image = multivector_image[0]
            yield (
                json.dumps(
                    {
                        "text": "Обработка представлений изображений...",
                        "images": [],
                    }
                )
                + "\n"
            ).encode("utf-8")
            await asyncio.sleep(0.5)

        # embedding -> database
        top_k = 5
        matches_query = vector_search(multivector_query, top_k)
        yield (
            json.dumps(
                {
                    "text": "Выполняется поиск по базе...",
                    "images": [],
                    "links": [],
                }
            )
            + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        matches_image = []
        if image_path:
            matches_image = vector_search(multivector_image, top_k)
            yield (
                json.dumps(
                    {
                        "text": "Продолжается поиск по базе...",
                        "images": [],
                        "links": [],
                    }
                )
                + "\n"
            ).encode("utf-8")

        sorted_matches = sorted(
            (matches_query + matches_image), key=lambda x: x.score, reverse=True
        )
        matches = unique_dicts(sorted_matches)
        matches = sorted_matches[:top_k]
        masks = await asyncio.gather(
            *[
                run_in_threadpool(
                    colpali_client.get_heatmap, query, m.get_preview_image_file()
                )
                for m in matches
            ]
        )
        alpha = 0.5
        heatmaps = [np.repeat(mask * (1 - alpha), 3, -1) for mask in masks]
        hm_imgs = [
            match.get_image() * alpha + heatmap
            for match, heatmap in zip(matches, heatmaps)
        ]
        hm_links = []
        base_hm_dir = Path("temp_masks/")
        for arr in hm_imgs:
            save_path = (
                base_hm_dir / datetime.now().strftime("%Y%m%d_%H%M%S%f")
            ).with_suffix(".jpg")
            hm_links.append(save_path)
            img = Image.fromarray(arr.astype(np.uint8))
            img.save(save_path, "JPEG")

        links_to_matches = [m.get_markdown_pdf_link() for m in matches]
        yield (
            json.dumps(
                {
                    "text": "Обработка данных...",
                    "images": [m.get_preview_image_file() for m in (matches)],
                    "heatmaps": [f"/heatmaps/{hm.name}" for hm in hm_links],
                    "links": [
                        [m.file_id.split("/")[-1], int(m.page_id) + 1] for m in matches
                    ],
                }
            )
            + "\n"
        ).encode("utf-8")

        # top-k documents -> llm
        await asyncio.sleep(0.5)
        llm_response = await run_in_threadpool(
            request_with_images,
            query,
            [Path(match.get_preview_image_file()) for match in matches],
        )
        yield (
            json.dumps(
                {
                    "text": substitute_objects(
                        llm_response,
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


async def describe_image(
    query: str, image_path: Path | None = None
) -> AsyncGenerator[bytes, None]:
    """Generate streaming search results with text and images."""
    try:
        multivector_query = await run_in_threadpool(colpali_client.embed_texts, [query])
        multivector_query = multivector_query[0]
        yield (
            json.dumps({"text": "Обработка текстовых представлений..."}) + "\n"
        ).encode("utf-8")
        await asyncio.sleep(0.5)

        if image_path:
            multivector_image = await run_in_threadpool(
                colpali_client.embed_images, [str(image_path)]
            )
            multivector_image = multivector_image[0]
            yield (
                json.dumps(
                    {
                        "text": "Обработка представлений изображений...",
                    }
                )
                + "\n"
            ).encode("utf-8")
            await asyncio.sleep(0.5)

        # top-k documents -> llm
        await asyncio.sleep(0.5)
        llm_response = await run_in_threadpool(
            request_with_images,
            query,
            [image_path],
        )
        yield (
            json.dumps(
                {
                    "text": llm_response,
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
    return StreamingResponse(search_with_image(q), media_type="application/x-ndjson")


@router.post("/api/describe")
async def describe(q: str = Form(...), image: UploadFile = File(None)):
    """Describe image by user query, returns streaming results."""
    if image and image.filename:
        # Save uploaded image temporarily
        temp_path = Path("temp_uploads")
        temp_path.mkdir(exist_ok=True)
        image_path = temp_path / image.filename
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        return StreamingResponse(
            describe_image(q, image_path), media_type="application/x-ndjson"
        )
    return StreamingResponse(describe_image(q), media_type="application/x-ndjson")


# Keep the GET endpoint for backward compatibility
@router.get("/api/search")
async def search_get(q: str):
    """Search endpoint that returns streaming results (GET method)."""
    return StreamingResponse(search_with_image(q), media_type="application/x-ndjson")
