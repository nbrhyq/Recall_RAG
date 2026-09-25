-- Production-oriented PostgreSQL / Supabase schema.
create extension if not exists vector;

create table documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  source_url text not null,
  platform text not null default 'douyin',
  title text not null,
  author text,
  collection_name text not null default '未分类',
  transcript text not null,
  summary text,
  duration_seconds numeric not null default 0,
  processing_status text not null default 'pending',
  source_type text not null default 'pdf',
  file_name text,
  page_count integer not null default 0,
  created_at timestamptz not null default now(),
  unique (user_id, source_url)
);

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  start_seconds numeric not null,
  end_seconds numeric not null,
  page_number integer,
  content text not null,
  embedding vector(1536),
  metadata jsonb not null default '{}'::jsonb
);

create index document_chunks_embedding_idx on document_chunks
using hnsw (embedding vector_cosine_ops);
