import math
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pdf2image import convert_from_path

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


def get_pdf_preview(pdf_path):
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
            pages = convert_from_path(pdf_path, first_page=1, last_page=1)
            if pages:
                Path(preview_path).parent.mkdir(parents=True, exist_ok=True)
                pages[0].save(str(preview_path), "JPEG")
                return f"/previews/{preview_name}"
        except Exception as e:
            print(f"Error generating preview for {pdf_path}: {e}")
            return None
    else:
        return f"/previews/{preview_name}"

    return None


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    uploaded_files = []
    for file in files:
        try:
            if not file.filename:
                raise HTTPException(status_code=400, detail="Filename is required")

            file_path = uploads_dir / file.filename
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            pages = convert_from_path(file_path, 300)
            for i, page in enumerate(pages):
                preview_path = f"previews/{Path(file_path).stem}{i}.jpg"
                Path(preview_path).parent.mkdir(parents=True, exist_ok=True)
                page.save(preview_path, "JPEG")

            file_data = {
                "name": file.filename,
                "type": get_file_type(file.filename),
                "size": os.path.getsize(file_path) / 1024,  # size in KB
                "path": str(file_path),
            }

            # Generate preview for PDFs
            if file_path.suffix.lower() == ".pdf":
                preview_url = get_pdf_preview(file_path)
                if preview_url:
                    file_data["preview_url"] = preview_url

            uploaded_files.append(file_data)

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to upload {file.filename}: {str(e)}"},
            )

    return JSONResponse(content={"files": uploaded_files})


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
                    preview_url = get_pdf_preview(file_path)
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
