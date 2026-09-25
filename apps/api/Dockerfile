FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-ocr.txt ./
RUN pip install --no-cache-dir -r requirements-ocr.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
