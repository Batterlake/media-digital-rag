from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import (
    COLPALI_PORT,
    COLPALI_URL,
    QDRANT_COLLECTION_NAME,
    QDRANT_KEY,
    QDRANT_URL,
)
from app.db import index_uploaded_files
from app.retriever.client import ColpaliClient

if __name__ == "__main__":
    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_KEY,
    )

    colpali_client = ColpaliClient(
        host=COLPALI_URL,
        port=COLPALI_PORT,
    )

    collection_name = QDRANT_COLLECTION_NAME

    if qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.delete_collection(collection_name=collection_name)

    qdrant_client.create_collection(
        collection_name=collection_name,
        on_disk_payload=True,  # store the payload on disk
        vectors_config=models.VectorParams(
            size=128,
            distance=models.Distance.COSINE,
            on_disk=True,  # move original vectors to disk
            multivector_config=models.MultiVectorConfig(
                comparator=models.MultiVectorComparator.MAX_SIM
            ),
            quantization_config=models.BinaryQuantization(
                binary=models.BinaryQuantizationConfig(
                    always_ram=True  # keep only quantized vectors in RAM
                ),
            ),
        ),
    )

    uploaded_files = [str(s) for s in Path("./previews").rglob("*.jpg")]

    index_uploaded_files(uploaded_files, 8)
