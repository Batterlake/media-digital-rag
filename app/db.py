from pathlib import Path

import numpy as np
import stamina
from qdrant_client import QdrantClient
from qdrant_client.http import models
from tqdm import tqdm

from app.config import QDRANT_COLLECTION_NAME, QDRANT_KEY, QDRANT_URL

from .retriever.client import ColpaliClient


def get_qdrant_client():
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_KEY,
    )


colpali_client = ColpaliClient("colpali", port=8000)


def get_payload_id_from_filename(filename: str):
    file_id = Path(filename).parent
    page_id = Path(filename).stem
    return {"file_id": file_id, "page_id": page_id}


@stamina.retry(
    on=Exception, attempts=3
)  # retry mechanism if an exception occurs during the operation
def upsert_to_qdrant(points):
    qdrant_client = get_qdrant_client()
    try:
        qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=points,
            wait=False,
        )
    except Exception as e:
        print(f"Error during upsert: {e}")
        return False
    return True


def index_uploaded_files(uploaded_files: list[Path], batch_size: int = 8):
    with tqdm(total=len(uploaded_files), desc="Indexing Progress") as pbar:
        for i in range(0, len(uploaded_files), batch_size):
            batch = uploaded_files[i : i + batch_size]

            # Process and encode images
            image_embeddings = colpali_client.embed_images(batch).astype(np.float32)

            # Prepare points for Qdrant
            points = []
            for j, embedding in enumerate(image_embeddings):
                # Convert the embedding to a list of vectors
                multivector = embedding.tolist()
                points.append(
                    models.PointStruct(
                        id=i + j,  # we just use the index as the ID
                        vector=multivector,  # This is now a list of vectors
                        payload=get_payload_id_from_filename(batch[j]),
                    )
                )

            # Upload points to Qdrant
            try:
                upsert_to_qdrant(points)
            except Exception as e:
                print(f"Error during upsert: {e}")
                continue

            # Update the progress bar
            pbar.update(batch_size)
    # get_qdrant_client().update_collection(
    #     collection_name=QDRANT_COLLECTION_NAME,
    #     optimizer_config=models.OptimizersConfigDiff(indexing_threshold=10),
    # ) # todo: find a better place to optimize index


def vector_search(multivector_query, top_k: int = 10):
    search_result = get_qdrant_client().query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=multivector_query,
        limit=top_k,
        timeout=100,
        search_params=models.SearchParams(
            quantization=models.QuantizationSearchParams(
                ignore=False,
                rescore=True,
                oversampling=2.0,
            )
        ),
    )
    payloads = [{**p.payload, "score": p.score} for p in search_result.points]
    return payloads
