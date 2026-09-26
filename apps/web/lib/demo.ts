import type { AskResult, Document } from "./types";

export const demoVideos: Document[] = [
  {
    id: "demo-1",
    url: "pdf://demo-reranker",
    title: "RAG 系统设计指南",
    author: "PDF 文档",
    collection: "AI / RAG",
    summary: "向量检索适合快速召回，Reranker 通过更精细的相关性计算减少无关上下文。",
    transcript: "RAG 的第一阶段通常使用向量检索快速召回候选文本。Reranker 会重新计算相关性。",
    duration: 0,
    status: "ready",
    created_at: new Date().toISOString(),
    source_type: "pdf",
    file_name: "RAG系统设计指南.pdf",
    page_count: 24,
  },
  {
    id: "demo-2",
    url: "pdf://demo-evaluation",
    title: "AI 产品评估手册",
    author: "PDF 文档",
    collection: "AI 产品经理",
    summary: "从检索命中、引用准确、回答相关与来源覆盖四个维度评估 RAG。",
    transcript: "评估 RAG 不能只看最终回答。首先看检索命中率，然后看引用准确率。",
    duration: 0,
    status: "ready",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    source_type: "pdf",
    file_name: "AI产品评估手册.pdf",
    page_count: 36,
  },
  {
    id: "demo-3",
    url: "pdf://demo-agent",
    title: "Agent 产品设计报告",
    author: "PDF 文档",
    collection: "AI 产品经理",
    summary: "从任务边界、用户控制和失败恢复理解 Agent 产品设计。",
    transcript: "Agent 的价值不在于无限自主，而在于明确任务边界并让用户保持控制。",
    duration: 0,
    status: "ready",
    created_at: new Date(Date.now() - 172800000).toISOString(),
    source_type: "pdf",
    file_name: "Agent产品设计报告.pdf",
    page_count: 18,
  },
];

const rerankerAnswer: AskResult = {
  answer: "Reranker 位于向量召回之后，会对候选片段进行更精细的相关性排序。它解决了“语义相似但不真正回答问题”的情况，减少送入大模型的无关上下文，从而提高回答准确率和引用质量。",
  grounded: true,
  confidence: 0.91,
  citations: [
    {
      document_id: "demo-1",
      title: "RAG 系统设计指南",
      author: "PDF 文档",
      url: "pdf://demo-reranker",
      start: 0,
      end: 0,
      quote: "Reranker 会把问题和候选文档一起输入交叉编码器，重新计算相关性，再把最可靠的几个片段交给大模型。",
      score: 0.94,
      source_type: "pdf",
      file_name: "RAG系统设计指南.pdf",
      page_number: 12,
    },
    {
      document_id: "demo-2",
      title: "AI 产品评估手册",
      author: "PDF 文档",
      url: "pdf://demo-evaluation",
      start: 0,
      end: 0,
      quote: "引用准确率用来确认检索到的片段是否真的支持最终回答。",
      score: 0.83,
      source_type: "pdf",
      file_name: "AI产品评估手册.pdf",
      page_number: 18,
    },
  ],
};

const evaluationAnswer: AskResult = {
  answer: "评估 RAG 产品不能只看回答是否流畅，需要拆开检索、引用、回答和拒答四个阶段。Recall 使用 Hit@1/3/5 与 MRR 衡量检索排序，并单独测试知识库没有答案时能否正确拒答。当前 45 题评测显示，Hybrid + Reranker 的 Hit@1 为 85.7%，Hit@3/5 为 100%，拒答准确率为 100%。",
  grounded: true,
  confidence: 0.89,
  citations: [
    { document_id: "demo-2", title: "AI 产品评估手册", author: "PDF 文档", url: "pdf://demo-evaluation", start: 0, end: 0, quote: "评估 RAG 不能只看最终回答。首先看检索命中率，然后检查引用是否真正支持回答。", score: 0.92, source_type: "pdf", file_name: "AI产品评估手册.pdf", page_number: 18 },
    { document_id: "demo-1", title: "RAG 系统设计指南", author: "PDF 文档", url: "pdf://demo-reranker", start: 0, end: 0, quote: "离线评测应同时包含可回答问题和知识库外问题，以测量错误回答与错误拒答。", score: 0.85, source_type: "pdf", file_name: "RAG系统设计指南.pdf", page_number: 21 },
  ],
};

const agentAnswer: AskResult = {
  answer: "Agent 产品设计首先要定义任务边界：哪些步骤可以自动执行，哪些高风险操作必须由用户确认。其次要让过程可观察、可中断，并为工具失败、信息不足和执行超时提供明确的恢复路径。自主程度越高，权限控制、状态反馈和失败恢复就越重要。",
  grounded: true,
  confidence: 0.87,
  citations: [
    { document_id: "demo-3", title: "Agent 产品设计报告", author: "PDF 文档", url: "pdf://demo-agent", start: 0, end: 0, quote: "Agent 的价值不在于无限自主，而在于明确任务边界，并让用户在关键节点保持控制。", score: 0.91, source_type: "pdf", file_name: "Agent产品设计报告.pdf", page_number: 8 },
    { document_id: "demo-3", title: "Agent 产品设计报告", author: "PDF 文档", url: "pdf://demo-agent", start: 0, end: 0, quote: "产品需要暴露执行状态，并为工具失败、超时和权限不足设计恢复路径。", score: 0.82, source_type: "pdf", file_name: "Agent产品设计报告.pdf", page_number: 14 },
  ],
};

const insufficientAnswer: AskResult = {
  answer: "当前静态演示知识库没有足够证据回答这个问题。请点击下方三个示例问题体验完整的检索、回答与引用界面；克隆项目并启动本地 API 后，可以上传自己的文档并自由提问。",
  grounded: false,
  confidence: 0,
  citations: [],
};

export function getDemoAnswer(question: string): AskResult {
  const normalized = question.toLowerCase();
  if (normalized.includes("reranker") || normalized.includes("重排")) return rerankerAnswer;
  if (normalized.includes("评估") || normalized.includes("指标")) return evaluationAnswer;
  if (normalized.includes("agent") || normalized.includes("智能体")) return agentAnswer;
  return insufficientAnswer;
}
