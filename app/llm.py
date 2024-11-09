import base64
from pathlib import Path

from openai import OpenAI


def encode_base64(image_path: str | Path):
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read())
    return encoded_image


def request_with_image(
    query_text: str | None,
    image_path: Path | None,
    system_prompt="You are a helpful assistant.",
    api_key="pee-pee-poo-poo",
    api_url="http://ml.n19:6336/v1",
):
    # Set OpenAI's API key and API base to use vLLM's API server.
    client = OpenAI(
        api_key=api_key,
        base_url=api_url,
    )

    image_query = []
    if image_path is not None:
        image_query = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f'data:image;base64,{encode_base64(image_path=image_path).decode("utf-8")}'
                },
            }
        ]

    text_query = []
    if query_text is not None:
        text_query = {
            "type": "text",
            "text": query_text,
        }
    chat_response = client.chat.completions.create(
        # model="Qwen2-VL-72B-Instruct-GPTQ-Int4",
        model="Qwen2-VL-7B-Instruct-GPTQ-Int4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": image_query + text_query},
        ],
    )
    return chat_response.choices[0].message.content
