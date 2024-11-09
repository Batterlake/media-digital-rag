import os
from itertools import islice

import numpy as np
import torch
from colpali_engine.interpretability import (
    get_similarity_maps_from_embeddings,
    normalize_similarity_map,
)
from colpali_engine.models import ColPali, ColPaliProcessor
from colpali_engine.utils.torch_utils import get_torch_device
from einops import rearrange
from fastapi import FastAPI, Request, Response, UploadFile
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
    texts = data["texts"]
    embeddings = []
    for batch in batched(texts, batch_size):
        with torch.inference_mode():
            inputs = processor.process_queries(batch).to(device)
            embeddings.append(model.forward(**inputs).cpu().to(torch.float16))
    return Response(
        content=torch.concatenate(embeddings).numpy().tobytes(),
        media_type="binary/octet-stream",
    )


@app.post("/heatmaps/")
async def get_heatmaps(query: str, image: UploadFile):
    image = Image.open(image.file)

    with torch.inference_mode():
        text_inputs = processor.process_queries([query]).to(device)
        query_embeddings = model.forward(**text_inputs).cpu().to(torch.float16)

    with torch.inference_mode():
        image_inputs = processor.process_images([image])
        image_mask = processor.get_image_mask(image_inputs)
        image_inputs = image_inputs.to(device)
        image_embeddings = model.forward(**image_inputs).cpu().to(torch.float16)
        n_patches = processor.get_n_patches(image_size=image.size, patch_size=14)

    similarity_maps = get_similarity_maps_from_embeddings(
        image_embeddings=image_embeddings,
        query_embeddings=query_embeddings,
        n_patches=n_patches,
        image_mask=image_mask,
    )[0]
    similarity_maps = [
        rearrange(
            normalize_similarity_map(sm).to(torch.float32).cpu().numpy(),
            "h w -> w h",
        )
        for sm in similarity_maps
    ]
    similarity_maps = [
        Image.fromarray((sm * 255).astype(np.uint8)).resize(
            image.size, Image.Resampling.BICUBIC
        )
        for sm in similarity_maps
    ]
    similarity_maps = [np.array(sm) for sm in similarity_maps]
    heatmap = np.median(similarity_maps, 0)[..., None]
    heatmap_mask = heatmap > np.percentile(heatmap, 97)
    heatmap[heatmap_mask == 0] = 0
    return Response(
        content=heatmap.tobytes(),
        media_type="binary/octet-stream",
    )
