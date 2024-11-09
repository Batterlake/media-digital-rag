import numpy as np
import requests
from PIL import Image


class ColpaliClient:
    IMAGE_ROUTE = "embed_images"
    TEXT_ROUTE = "embed_texts"
    HEATMAPS_ROUTE = "heatmaps"
    EMBEDDING_DIM = 128

    def __init__(self, url: str):
        self.url = url

    def embed_images(self, filenames: list[str]) -> np.ndarray | None:
        files = [("images", (image, open(image, "rb"))) for image in filenames]
        url = f"{self.url}/{self.IMAGE_ROUTE}/"
        response = requests.post(
            url,
            files=files,
        )
        try:
            embeds = np.frombuffer(response.content, dtype=np.float16).reshape(
                len(filenames), -1, 128
            )
        except Exception:
            embeds = None
        return embeds

    def embed_texts(self, texts: list[str]) -> np.ndarray | None:
        url = f"{self.url}/{self.TEXT_ROUTE}/"
        response = requests.post(
            url,
            json={"texts": texts},
        )
        try:
            embeds = np.frombuffer(response.content, dtype=np.float16).reshape(
                len(texts), -1, 128
            )
        except Exception:
            embeds = None
        return embeds

    def get_heatmap(self, query: str, image: str) -> np.ndarray | None:
        url = f"{self.url}/{self.HEATMAPS_ROUTE}/"
        response = requests.post(
            url, params={"query": query}, files={"image": open(image, "rb")}
        )
        try:
            image_size = Image.open(image).size
            data = np.frombuffer(response.content, dtype=np.float64)
            heatmap = data.reshape(*image_size[::-1], 1)
        except Exception:
            heatmap = None
        return heatmap
