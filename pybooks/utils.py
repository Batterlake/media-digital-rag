import base64
from pathlib import Path

from openai import OpenAI


def request_with_image(
    query_text: str,
    image_path: Path,
    system_prompt="You are a helpful assistant.",
    api_key="pee-pee-poo-poo",
    api_url="http://ml.n19:6336/v1",
):
    # Set OpenAI's API key and API base to use vLLM's API server.
    client = OpenAI(
        api_key=api_key,
        base_url=api_url,
    )
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read())
    encoded_image_text = encoded_image.decode("utf-8")
    base64_qwen = f"data:image;base64,{encoded_image_text}"
    chat_response = client.chat.completions.create(
        # model="Qwen2-VL-72B-Instruct-GPTQ-Int4",
        model="Qwen2-VL-7B-Instruct-GPTQ-Int4",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": base64_qwen},
                    },
                    {
                        "type": "text",
                        "text": query_text,
                    },
                ],
            },
        ],
    )
    return chat_response
