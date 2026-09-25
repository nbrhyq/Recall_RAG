"use client";

import "./controls.css";

import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, BookOpen, Check, ChevronRight, FileText, Image as ImageIcon, Library, Plus, Sparkles, Trash2, Type, Upload, X } from "lucide-react";
import { addImage, addPdf, addText, askQuestion, deleteDocument, documentFileUrl, getDocuments } from "@/lib/api";
import type { AskResult, Document } from "@/lib/types";

const suggestions = ["Reranker 在 RAG 中有什么作用？", "怎样评估一个 RAG 产品？", "Agent 产品设计要注意什么？"];

function formatTime(seconds: number) {
  const min = Math.floor(seconds / 60).toString().padStart(2, "0");
  const sec = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${min}:${sec}`;
}

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [demo, setDemo] = useState(false);
  const [modal, setModal] = useState(false);
  const [notice, setNotice] = useState("");
  const [inputMode, setInputMode] = useState<"pdf" | "text" | "image">("pdf");
  const [ingesting, setIngesting] = useState(false);

  useEffect(() => {
    getDocuments().then((result) => { setDocuments(result.documents); setDemo(result.demo); });
  }, []);

  const topics = useMemo(() => new Set(documents.map((document) => document.collection)).size, [documents]);

  async function submit(value = question) {
    if (!value.trim() || loading) return;
    setQuestion(value);
    setLoading(true);
    setAnswer(null);
    try {
      const result = await askQuestion(value);
      setAnswer(result);
      requestAnimationFrame(() => document.querySelector("#answer")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "问答失败，请检查本地服务");
      setTimeout(() => setNotice(""), 5000);
    } finally {
      setLoading(false);
    }
  }

  async function handlePdf(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    setIngesting(true);
    try {
      const document = await addPdf(file, String(data.get("title")));
      setDocuments((current) => [document, ...current]);
      setModal(false);
      setNotice(`PDF 已提取 ${document.page_count} 页并加入知识库`);
      setTimeout(() => setNotice(""), 3500);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "PDF 上传失败");
      setTimeout(() => setNotice(""), 4000);
    } finally {
      setIngesting(false);
    }
  }

  async function handleImage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    setIngesting(true);
    try {
      const document = await addImage(file, String(data.get("title")));
      setDocuments((current) => [document, ...current]);
      setModal(false);
      setNotice("图片文字已识别、分类并加入知识库");
      setTimeout(() => setNotice(""), 3500);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "图片上传失败");
      setTimeout(() => setNotice(""), 4000);
    } finally {
      setIngesting(false);
    }
  }

  async function handleText(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setIngesting(true);
    try {
      const document = await addText(String(data.get("title")), String(data.get("content")));
      setDocuments((current) => [document, ...current]);
      setModal(false);
      setNotice("文字已自动分类并加入知识库");
      setTimeout(() => setNotice(""), 3500);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "文字添加失败");
      setTimeout(() => setNotice(""), 4000);
    } finally {
      setIngesting(false);
    }
  }

  async function removeDocument(item: Document) {
    if (!window.confirm(`确定删除“${item.title}”吗？对应索引和原文件也会删除。`)) return;
    try {
      await deleteDocument(item.id);
      setDocuments((current) => current.filter((document) => document.id !== item.id));
      setNotice("知识条目已删除");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "删除失败");
    }
    setTimeout(() => setNotice(""), 3500);
  }

  return (
    <main>
      <nav className="nav shell">
        <a className="brand" href="#top" aria-label="Recall 首页"><span className="brand-mark">R</span><span>Recall</span></a>
        <div className="nav-links">
          <a className="active" href="#ask"><Sparkles size={16} /> 问知识库</a>
          <a href="#library"><Library size={16} /> 收藏库</a>
          <a href="#insight"><BookOpen size={16} /> 产品洞察</a>
        </div>
        <button className="button dark small" onClick={() => setModal(true)}><Plus size={16} /> 添加知识</button>
      </nav>

      <section className="hero shell" id="top">
        <div className="eyebrow"><span className="pulse" /> Qwen3 驱动的个人文档知识库</div>
        <h1>让读过的文档，<br /><em>变成随时可用的知识。</em></h1>
        <p className="hero-copy">上传 PDF 或图片，也可以直接输入文字。Recall 自动识别、分类并沉淀内容，让每个答案都有出处。</p>

        <div className="ask-card" id="ask">
          <div className="ask-top"><Sparkles size={20} /><span>向你的知识库提问</span><span className="scope">全部内容 · {documents.length} 条</span></div>
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} placeholder="例如：Reranker 在 RAG 中有什么作用？" rows={3} />
          <div className="ask-footer"><span>由本地 Qwen3 基于 PDF 证据回答</span><button aria-label="提交问题" onClick={() => submit()} disabled={loading}><ArrowUpRight size={21} /></button></div>
        </div>
        <div className="suggestions"><span>试着问：</span>{suggestions.map((item) => <button key={item} onClick={() => submit(item)}>{item}</button>)}</div>
      </section>

      {answer && (
        <section className="answer-section shell" id="answer">
          <div className="section-kicker">ANSWER</div>
          <div className="answer-grid">
            <article className="answer-card">
              <div className={`grounding ${answer.grounded ? "good" : "weak"}`}><Check size={15} /> {answer.grounded ? `已由 ${answer.citations.length} 条收藏验证` : "知识库证据不足"}</div>
              <h2>{question}</h2>
              <p>{answer.answer}</p>
              {answer.grounded && <div className="confidence"><span>回答可信度</span><div><i style={{ width: `${answer.confidence * 100}%` }} /></div><b>{Math.round(answer.confidence * 100)}%</b></div>}
            </article>
            <aside className="sources">
              <div className="source-heading"><span>引用来源</span><small>{answer.citations.length} 个片段</small></div>
              {answer.citations.map((citation, index) => (
                <a className="source-card" key={`${citation.document_id}-${index}`} href={citation.source_type === "text" ? undefined : documentFileUrl(citation.document_id)} target={citation.source_type === "text" ? undefined : "_blank"} rel="noreferrer">
                  <div className="source-number">{String(index + 1).padStart(2, "0")}</div>
                  <div><h3>{citation.title}</h3><span>{citation.source_type === "pdf" ? `${citation.file_name} · 第 ${citation.page_number} 页` : citation.source_type === "image" ? `${citation.file_name} · 图片 OCR` : "手动输入文字"}</span><blockquote>“{citation.quote}”</blockquote></div>
                  {citation.source_type === "image" ? <ImageIcon size={16} /> : citation.source_type === "text" ? <Type size={16} /> : <FileText size={16} />}
                </a>
              ))}
            </aside>
          </div>
        </section>
      )}

      {loading && <section className="loading shell"><span /><p>正在检索收藏并核对引用…</p></section>}

      <section className="library-section" id="library">
        <div className="shell">
          <div className="section-head"><div><div className="section-kicker">YOUR LIBRARY</div><h2>最近沉淀的知识</h2></div><button className="text-button">查看全部 <ChevronRight size={17} /></button></div>
          <div className="metrics"><div><strong>{documents.length}</strong><span>知识条目</span></div><div><strong>{topics}</strong><span>自动分类</span></div><div><strong>100%</strong><span>本地模型</span></div></div>
          <div className="video-grid">
            {documents.map((document, index) => (
              <article className="video-card" key={document.id}>
                <div className={`cover cover-${index % 3}`}><span className="tag">{document.collection}</span><button aria-label="查看内容">{document.source_type === "image" ? <ImageIcon size={20} /> : document.source_type === "text" ? <Type size={20} /> : <FileText size={20} />}</button><small>{document.source_type === "pdf" ? <><FileText size={13} /> {document.page_count} 页</> : document.source_type === "image" ? <><ImageIcon size={13} /> 图片 OCR</> : <><Type size={13} /> 文字笔记</>}</small></div>
                <div className="video-body"><span>{document.file_name || (document.source_type === "text" ? "手动输入" : "图片 OCR")}</span><h3>{document.title}</h3><p>{document.summary}</p><div><span className="ready"><i /> 已完成索引</span><button className="delete-button" aria-label={`删除 ${document.title}`} onClick={() => removeDocument(document)}><Trash2 size={16} /></button></div></div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="insight shell" id="insight">
        <div><div className="section-kicker">WHY RECALL</div><h2>从“我好像看过”，<br />到“这是原始依据”。</h2></div>
        <div className="principles">
          <div><span>01</span><h3>知识自动整理</h3><p>Qwen3 自动生成摘要和分类，无需手动维护文件夹。</p></div>
          <div><span>02</span><h3>答案有据可查</h3><p>每个关键结论都回到原 PDF 和准确页码。</p></div>
          <div><span>03</span><h3>不知道就不编</h3><p>证据不足时明确告知，把回答边界交还给用户。</p></div>
        </div>
      </section>

      <footer className="shell"><div className="brand"><span className="brand-mark">R</span><span>Recall</span></div><p>Built as a source-grounded AI product case study.</p><span>© 2026</span></footer>

      {demo && <div className="demo-pill">演示模式 · 启动 API 后使用真实数据</div>}
      {notice && <div className="toast">{notice}</div>}
      {modal && (
        <div className="modal-backdrop" onMouseDown={() => setModal(false)}>
          <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setModal(false)}><X size={19} /></button>
            <div className="modal-icon">{inputMode === "pdf" ? <FileText size={22} /> : inputMode === "image" ? <ImageIcon size={22} /> : <Type size={22} />}</div><h2>添加知识</h2><p>Qwen3 会在本地自动生成摘要和分类，内容不会发送到云端。</p>
            <div className="mode-tabs three"><button className={inputMode === "pdf" ? "active" : ""} onClick={() => setInputMode("pdf")}><FileText size={14} /> PDF</button><button className={inputMode === "text" ? "active" : ""} onClick={() => setInputMode("text")}><Type size={14} /> 文字</button><button className={inputMode === "image" ? "active" : ""} onClick={() => setInputMode("image")}><ImageIcon size={14} /> 图片</button></div>
            {inputMode === "pdf" ? <form onSubmit={handlePdf}>
              <label className="file-drop"><Upload size={25} /><strong>选择 PDF 文件</strong><span>最大 20MB · 扫描件自动 OCR · 保留页码</span><input name="file" type="file" accept="application/pdf,.pdf" required /></label>
              <label>文档名称（可选）<input name="title" placeholder="默认使用文件名" /></label>
              <button className="button dark submit" type="submit" disabled={ingesting}>{ingesting ? "正在解析、分类和建立索引…" : "自动识别并分类"} <ArrowUpRight size={17} /></button>
            </form> : inputMode === "text" ? <form onSubmit={handleText}>
              <label>标题<input name="title" placeholder="例如：关于 RAG 评估的笔记" minLength={2} required /></label>
              <label>文字内容<textarea name="content" rows={9} placeholder="输入或粘贴需要保存到知识库的内容…" minLength={10} required /></label>
              <button className="button dark submit" type="submit" disabled={ingesting}>{ingesting ? "正在分类和建立索引…" : "自动分类并保存"} <ArrowUpRight size={17} /></button>
            </form> : <form onSubmit={handleImage}>
              <label className="file-drop"><Upload size={25} /><strong>选择图片</strong><span>PNG、JPG 或 WebP · 最大 10MB · 自动 OCR</span><input name="file" type="file" accept="image/png,image/jpeg,image/webp" required /></label>
              <label>内容名称（可选）<input name="title" placeholder="默认使用文件名" /></label>
              <button className="button dark submit" type="submit" disabled={ingesting}>{ingesting ? "正在 OCR 和建立索引…" : "识别、分类并保存"} <ArrowUpRight size={17} /></button>
            </form>}
          </div>
        </div>
      )}
    </main>
  );
}
