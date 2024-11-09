import numpy as np
import requests


class ColpaliClient:
    IMAGE_ROUTE = "embed_images"
    TEXT_ROUTE = "embed_texts"
    EMBEDDING_DIM = 128

    def __init__(self, host: str, port: int):
        self.url = f"http://{host}:{port}"

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
