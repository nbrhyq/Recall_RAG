# Recall — Local PDF knowledge assistant

Recall turns PDFs, images, and pasted text into a searchable, source-grounded personal knowledge base. Local Qwen3 classifies and summarises every item, then answers questions from retrieved evidence.

This repository is an AI Product Manager portfolio MVP. It deliberately runs without paid services: the API includes local SQLite storage and a deterministic hybrid retrieval fallback. OpenAI-compatible generation can be enabled with environment variables.

## Product flow

1. Upload a text/scanned PDF, upload an image, or paste text.
2. Recall extracts or OCRs the content and preserves PDF page numbers.
3. Local Qwen3 automatically classifies and summarises the document.
3. Ask across the personal library.
4. Receive a grounded synthesis and clickable source cards.
5. If evidence is weak, Recall says the library is insufficient instead of inventing an answer.

## Repository

- `apps/web` — Next.js product interface
- `apps/api` — FastAPI ingestion and RAG API
- `docs` — product decisions, evaluation plan, and database schema

## Run locally

### API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ocr.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Run Ollama in another terminal. The project uses the installed `qwen3:latest` model by default:

```bash
ollama serve
ollama pull qwen3-embedding:0.6b
ollama list
```

### Web

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend loads built-in demo content when the API is unavailable, so the product can still be reviewed as a UI prototype.

## API

- `GET /health`
- `GET /api/documents`
- `POST /api/pdfs` — multipart PDF upload, maximum 20MB
- `POST /api/images` — PNG/JPG/WebP upload, maximum 10MB
- `POST /api/texts` — manually entered title and content
- `POST /api/ask`

Interactive documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Current MVP boundary

PDF pages first use native text extraction; pages without text and uploaded images use local PaddleOCR. Classification, summaries, and grounded answers run through `qwen3:latest` on the user's local Ollama service, so knowledge content stays local.

Retrieval uses a three-stage local pipeline:

1. Qwen3 Embedding 0.6B writes semantic vectors to persistent Qdrant local storage.
2. Keyword and vector results are merged into a hybrid candidate set.
3. Qwen3 reranks candidates before generating a citation-grounded answer.

See [docs/PRODUCT.md](docs/PRODUCT.md) for scope and [docs/EVALUATION.md](docs/EVALUATION.md) for the quality framework.
