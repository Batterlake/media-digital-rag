FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 python3-pip python3-dev python-is-python3 wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install fastapi==0.115.4 colpali_engine==0.3.4
RUN pip install fastapi[standard]
RUN pip install einops
RUN pip install matplotlib
RUN pip install "colpali-engine[interpretability]"

COPY . /app

ENTRYPOINT ["fastapi", "run", "server.py"]
