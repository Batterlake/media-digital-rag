import base64
from pathlib import Path

from openai import OpenAI

from app.config import LLM_KEY, LLM_MODEL, LLM_URL

SYSTEM_PROMPT = """
You're a helpfull assistant. Answer the user's question based on provided context. Be brief ans consice.
"""


def encode_base64(image_path: str | Path):
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read())
    return encoded_image


def request_with_images(
    query_text: str | None,
    image_paths: list[Path] | None,
    # image_contexts: list[Path] | None,
    system_prompt=SYSTEM_PROMPT,
    api_key=LLM_KEY,
    api_url=LLM_URL,
):
    # Set OpenAI's API key and API base to use vLLM's API server.
    client = OpenAI(
        api_key=api_key,
        base_url=api_url,
    )

    image_query = []
    if image_paths is not None:
        image_query = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image;base64,{encode_base64(image_path=image_path).decode('utf-8')}"
                },
            }
            for image_path in image_paths
        ]

    text_query = []
    if query_text is not None:
        text_query = [
            {
                "type": "text",
                "text": query_text,
            }
        ]
    chat_response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": image_query + text_query},
        ],
    )
    return (
        chat_response.choices[0]
        .message.content.encode("utf-8")
        .decode("utf-8", errors="replace")
    )
