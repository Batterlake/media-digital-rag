from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from pdf2image import convert_from_path

DATA_PATH = Path("./data/")
PDFS_ROOT = DATA_PATH / "pdfs"
JPEG_ROOT = DATA_PATH / "jpeg"
router = APIRouter(prefix="/files", tags=["Работа с .pdf файлами"])


@router.post("/", summary="Загрузить файл")
async def upload_file(file: UploadFile = File(...)):
    filename = PDFS_ROOT / Path(file.filename).name
    if filename.is_file():
        raise HTTPException(502, "Файл с таким именем уже существует")
    async with aiofiles.open(filename, "wb") as out_file:
        while content := await file.read(1024):  # async read chunk
            await out_file.write(content)  # async write chunk

    # subprocess.call(["tools/convert-pdf.sh", f'"{filename}"', JPEG_ROOT]) # does not work for some reason for space separated filenames

    jpeg_folder = JPEG_ROOT / Path(file.filename).name
    if jpeg_folder.is_dir():
        raise HTTPException(502, "Папка для данного файла уже существует")
    jpeg_folder.mkdir()
    pages = convert_from_path(filename, 300)
    for i, page in enumerate(pages):
        page.save(jpeg_folder / f"{i}.jpg", "JPEG")
    return {"Result": "OK"}


@router.get("/", summary="Получить все файлы")
async def get_all_files():
    files = PDFS_ROOT.glob("*.pdf")
    return [f.name for f in sorted(files, key=lambda x: x.stem)]


@router.get("/{uid}", summary="Загрузить файл")
async def get_file(uid: str):
    file: Path = PDFS_ROOT / uid
    if not file.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file)


def get_file_pages(folder: str | Path):
    folder = Path(folder)
    return sorted(folder.glob("*"), key=lambda x: x.stem)


@router.get("/{uid}/preview/", summary="Загрузить первую страницу")
async def preview(uid: str):
    pages = get_file_pages(JPEG_ROOT / Path(uid))
    if len(pages) == 0:
        raise HTTPException(status_code=404, detail="Страницы файла не найдены")
    first_page = pages[0]
    if not first_page.is_file():
        raise HTTPException(status_code=404, detail="Первая страница файла не найдена")
    return FileResponse(first_page)


@router.get("/{uid}/pages/", summary="Получить страницы файла")
async def get_file_pages_names(uid: str):
    pages = get_file_pages(JPEG_ROOT / Path(uid))
    if len(pages) == 0:
        raise HTTPException(
            status_code=404,
            detail="Запрашиваемый файл не найден",
        )
    names = [p.name for p in pages]
    return names


@router.get("/{uid}/pages/{page}", summary="Загрузить страницу с номером 'page'")
async def get_file_page(uid: str, page: str):
    page: Path = JPEG_ROOT / Path(uid) / page
    if not page.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Запрашиваемая страница не найдена: {page}",
        )

    return FileResponse(page)
