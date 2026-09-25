export type Document = {
  id: string;
  url: string;
  title: string;
  author: string;
  collection: string;
  summary: string;
  transcript: string;
  duration: number;
  status: string;
  created_at: string;
  source_type?: "pdf" | "image" | "text";
  file_name?: string | null;
  page_count?: number;
};

export type Citation = {
  document_id: string;
  title: string;
  author: string;
  url: string;
  start: number;
  end: number;
  quote: string;
  score: number;
  source_type?: "pdf" | "image" | "text";
  file_name?: string | null;
  page_number?: number | null;
};

export type AskResult = {
  answer: string;
  citations: Citation[];
  grounded: boolean;
  confidence: number;
};
