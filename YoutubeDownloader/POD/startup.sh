#!/bin/bash

gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --limit-request-field_size 52428800 \
  --timeout 120