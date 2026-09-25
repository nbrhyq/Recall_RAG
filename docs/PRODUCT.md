# Recall product brief

## Problem

People collect PDFs, screenshots, and notes but cannot recover the right idea when it matters. Folder structures are manual, documents are slow to scan, and a general chatbot cannot cite a user's private library.

## Target user

Knowledge workers and students who collect PDF research around AI, finance, product, or career development.

## Job to be done

> When I need an idea I remember reading, help me recover and apply it without searching every PDF, while showing exactly which page supports the answer.

## MVP scope

- Upload PDFs up to 20MB/100 pages, extract native text, and automatically OCR scanned pages with PaddleOCR.
- Upload PNG/JPG/WebP images and extract their text with PaddleOCR.
- Paste a titled text note directly into the knowledge base.
- Preserve page numbers during chunking.
- Use local Qwen3 to create the topic and summary automatically.
- Ask across all PDFs or an automatically generated category.
- Return a grounded response with the source filename/page or manual-text label and supporting quote.
- Refuse to invent an answer when retrieval evidence is weak.

## Deliberate non-goals

- Model training or custom vector infrastructure.
- Multi-user collaboration and enterprise permissions.

## Product principles

1. **Evidence before fluency** — a modest sourced answer is better than a polished unsupported one.
2. **Zero-friction organisation** — users upload a PDF; Qwen3 handles classification and summary locally.
3. **Progressive disclosure** — show the synthesis first and evidence cards immediately beside it.
4. **Replaceable AI services** — ASR, OCR, embedding, reranking, and generation are adapters, not product dependencies.

## Roadmap

- V0: PDF ingestion, OCR, local classification, retrieval, citations, library UI.
- V1: semantic embeddings, reranker, PDF preview, and page deep links.
- Current retrieval: Qwen3 Embedding + persistent Qdrant + keyword hybrid recall + Qwen3 listwise reranking.
- V2: collections, feedback loop, evaluation dashboard, cross-platform ingestion.
