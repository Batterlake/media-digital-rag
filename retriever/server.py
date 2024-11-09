import os
from itertools import islice

import torch
from colpali_engine.models import ColPali, ColPaliProcessor
from colpali_engine.utils.torch_utils import get_torch_device
from fastapi import FastAPI, Request, UploadFile, Response
from PIL import Image

device = get_torch_device("auto")
batch_size = int(os.environ.get("batch_size", 8))

model_name = "vidore/colpali-v1.2"
model = ColPali.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map=device,
).eval()
processor = ColPaliProcessor.from_pretrained(model_name)

app = FastAPI()


def batched(iterable, n):
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


@app.post("/embed_images/")
async def embed_images(
    images: list[UploadFile],
):
    embeddings = []
    for batch in batched(images, batch_size):
        batch = [Image.open(image.file) for image in batch]
        with torch.inference_mode():
            inputs = processor.process_images(batch).to(device)
            embeddings.append(model.forward(**inputs).cpu().to(torch.float16))
    return Response(
        content=torch.concatenate(embeddings).numpy().tobytes(),
        media_type="binary/octet-stream",
    )

@app.post("/embed_texts/")
async def embed_texts(request: Request):
    data = await request.json()
    texts = data['texts'] 
    embeddings = []
    for batch in batched(texts, batch_size):
        with torch.inference_mode():
            inputs = processor.process_queries(batch).to(device)
            embeddings.append(model.forward(**inputs).cpu().to(torch.float16))
    return Response(
        content=torch.concatenate(embeddings).numpy().tobytes(),
        media_type="binary/octet-stream",
    )
