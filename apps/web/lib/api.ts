import { demoAnswer, demoVideos } from "./demo";
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
  return response.json();
}

export async function getDocuments(): Promise<{ documents: Document[]; demo: boolean }> {
  try {
    return { documents: await request<Document[]>("/api/documents"), demo: false };
  } catch {
    return { documents: demoVideos, demo: true };
  }
}

export async function askQuestion(question: string, collection?: string): Promise<AskResult> {
  try {
    return await request<AskResult>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question, collection: collection || null }),
    });
  } catch {
    if (question.toLowerCase().includes("rerank") || question.includes("重排")) return demoAnswer;
    return {
      answer: "当前演示知识库没有足够信息回答这个问题。启动 API 或添加相关 PDF 后再试，我不会用文档之外的信息补全答案。",
      citations: [],
      grounded: false,
      confidence: 0,
    };
  }
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
