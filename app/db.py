from pathlib import Path

import numpy as np
import stamina
from PIL import Image
from qdrant_client.http import models
from tqdm import tqdm

from app.main import COLLECTION_NAME, get_qdrant_client


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
            collection_name=COLLECTION_NAME,
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

            # The images are already PIL Image objects, so we can use them directly
            images = [Image.open(el) for el in batch]

            # Process and encode images
            # with torch.no_grad():
            #     batch_images = colpali_processor.process_images(images).to(
            #         colpali_model.device
            #     )
            #     image_embeddings = colpali_model(**batch_images)
            image_embeddings = np.random.uniform(
                0, 1, size=(len(images), 500, 128)
            ).astype(np.float32)

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
