FROM python:3.11

RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 wget libvips poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock

RUN pip install poetry
RUN poetry install

COPY . /app

ENTRYPOINT ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--port", "8000", "--host", "0.0.0.0"]
