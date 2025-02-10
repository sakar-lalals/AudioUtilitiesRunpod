FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

RUN apt-get update; apt-get install -y ffmpeg
RUN python -m pip install --upgrade pip

WORKDIR /app

COPY YoutubeDownloader/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY utils/ utils/
COPY YoutubeDownloader/ YoutubeDownloader/
