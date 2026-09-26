import { demoVideos } from "./demo";
import type { AskResult, Document } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(detail.detail || "请求失败");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function getDocuments(): Promise<{ documents: Document[]; demo: boolean }> {
  if (process.env.NEXT_PUBLIC_STATIC_DEMO === "true") {
    return { documents: demoVideos, demo: true };
  }
  try {
    return { documents: await request<Document[]>("/api/documents"), demo: false };
  } catch {
    return { documents: demoVideos, demo: true };
  }
}

export async function askQuestion(question: string, collection?: string): Promise<AskResult> {
  return request<AskResult>("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question, collection: collection || null }),
  });
}

export async function addPdf(file: File, title: string): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  const response = await fetch(`${API_URL}/api/pdfs`, { method: "POST", body: form });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "PDF 上传失败" }));
    throw new Error(detail.detail || "PDF 上传失败");
  }
  return response.json();
}

export async function addImage(file: File, title: string): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  const response = await fetch(`${API_URL}/api/images`, { method: "POST", body: form });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "图片上传失败" }));
    throw new Error(detail.detail || "图片上传失败");
  }
  return response.json();
}

export async function addText(title: string, content: string): Promise<Document> {
  return request<Document>("/api/texts", {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export async function deleteDocument(id: string): Promise<void> {
  await request<void>(`/api/documents/${id}`, { method: "DELETE" });
}

export function documentFileUrl(id: string): string {
  return `${API_URL}/api/documents/${id}/file`;
}
