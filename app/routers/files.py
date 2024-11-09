import asyncio
import json
import math
import os
from pathlib import Path
from typing import List, Optional

import pyvips
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    StreamingResponse,
)

from ..db import index_uploaded_files

router = APIRouter()


def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.lower().split(".")[-1]
    if ext in ["jpg", "jpeg", "png", "gif"]:
        return "image"
    elif ext in ["mp4", "avi", "mov"]:
        return "video"
    elif ext in ["pdf", "doc", "docx"]:
        return "document"
    else:
        return "file"


def get_pdf_first_page(pdf_path):
    """Generate preview image for PDF first page"""
    # Create temp directory for preview images
    preview_dir = Path("previews/")
    preview_dir.mkdir(exist_ok=True)

    # Generate preview filename
    preview_name = f"{Path(pdf_path).stem}/0.jpg"
    preview_path = preview_dir / preview_name

    # Only generate preview if it doesn't exist
    if not preview_path.exists():
        try:
            # Convert first page of PDF to image
            page = pyvips.Image.new_from_file(str(pdf_path), dpi=100, page=0)
            if page:
                Path(preview_path).parent.mkdir(parents=True, exist_ok=True)
                page.write_to_file(str(preview_path))
                return f"/previews/{preview_name}"
        except Exception as e:
            print(f"Error generating preview for {pdf_path}: {e}")
            return None
    else:
        return f"/previews/{preview_name}"

    return None


async def send_progress(progress):
    """Helper function to send progress with proper newline and flush"""
    yield json.dumps(progress) + "\n"
    await asyncio.sleep(0.1)  # Small delay to ensure progress is sent


async def process_upload(files: List[Path]):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    uploaded_files = []
    uploaded_pages = []

    try:
        # Then process each saved file
        for file_path in files:
            try:
                # Convert PDF progress
                async for chunk in send_progress(
                    {
                        "stage": "converting",
                        "file": file_path.name,
                        "progress": 0,
                        "message": f"Converting {file_path.name}...",
                    }
                ):
                    yield chunk

                total_pages = pyvips.Image.new_from_file(str(file_path)).get("n-pages")
                for i in range(total_pages):
                    page = pyvips.Image.new_from_file(str(file_path), dpi=100, page=i)
                    preview_path = f"previews/{file_path.stem}/{i}.jpg"
                    Path(preview_path).parent.mkdir(parents=True, exist_ok=True)
                    page.write_to_file(preview_path)
                    uploaded_pages.append(preview_path)

                    # Update conversion progress
                    async for chunk in send_progress(
                        {
                            "stage": "converting",
                            "file": file_path.name,
                            "progress": (i + 1) / total_pages * 100,
                            "message": f"Converting page {i + 1} of {total_pages} for {file_path.name}...",
                        }
                    ):
                        yield chunk

                file_data = {
                    "name": file_path.name,
                    "type": get_file_type(file_path.name),
                    "size": os.path.getsize(file_path) / 1024,  # size in KB
                    "path": str(file_path),
                    "preview_url": f"previews/{file_path.stem}/0.jpg",
                }

                uploaded_files.append(file_data)

            except Exception as e:
                async for chunk in send_progress(
                    {"error": f"Failed to process {file_path.name}: {str(e)}"}
                ):
                    yield chunk
                return

        if uploaded_pages:
            # Indexing progress
            async for chunk in send_progress(
                {
                    "stage": "indexing",
                    "progress": 50,
                    "message": "Indexing uploaded files...",
                }
            ):
                yield chunk

            # Index the files
            index_uploaded_files(uploaded_pages)

        # Complete
        async for chunk in send_progress(
            {
                "stage": "complete",
                "progress": 100,
                "message": "Upload complete",
                "files": uploaded_files,
            }
        ):
            yield chunk

    except Exception as e:
        async for chunk in send_progress({"error": f"Upload failed: {str(e)}"}):
            yield chunk


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    saved_files = []

    for file in files:
        if not file.filename:
            return "Failed"

        file_path = uploads_dir / file.filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files.append(file_path)

    return StreamingResponse(
        process_upload(saved_files),
        media_type="text/event-stream",
    )


@router.get("/files", response_class=HTMLResponse)
async def files(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    items_per_page: int = 12,
):
    # Get files from uploads directory
    uploads_dir = Path("uploads")
    all_files = []

    if uploads_dir.exists():
        for file_path in uploads_dir.iterdir():
            if file_path.is_file():
                # Skip files that don't match search term
                if search and search.lower() not in file_path.name.lower():
                    continue

                file_type = get_file_type(file_path.name)
                file_data = {
                    "name": file_path.name,
                    "type": file_type,
                    "size": os.path.getsize(file_path) / 1024,  # size in KB
                    "path": str(file_path),
                }

                # Generate preview URL for PDFs
                if file_path.suffix.lower() == ".pdf":
                    preview_url = get_pdf_first_page(file_path)
                    if preview_url:
                        file_data["preview_url"] = preview_url

                all_files.append(file_data)

    # Sort files by name
    all_files.sort(key=lambda x: x["name"])

    # Calculate pagination
    total_files = len(all_files)
    total_pages = math.ceil(total_files / items_per_page)
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page

    # Get files for current page
    files_data = all_files[start_idx:end_idx]

    return request.app.state.templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "files": files_data,
            "current_page": page,
            "total_pages": total_pages,
            "search": search or "",
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    )


@router.get("/pdf/{filename}")
async def get_pdf(filename: str):
    file_path = Path("uploads") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",  # This makes the browser render the PDF instead of downloading it
    )
