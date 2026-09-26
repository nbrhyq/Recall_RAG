import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Check, CircleAlert, Database, FileSearch, Github, Layers3, ShieldCheck, Sparkles } from "lucide-react";
import "./case-study.css";

const versions = [
  { name: "V0", title: "Keyword", hit: "82.9%", recall: "97.1%", refusal: "80%", latency: "1 ms", note: "建立快速、可解释的词法基线，但无法稳定处理用户与原文措辞不同的问题。" },
  { name: "V1", title: "Embedding", hit: "77.1%", recall: "100%", refusal: "80%", latency: "93 ms", note: "正确页面全部进入 Top 5，但同主题中“相关却不回答问题”的片段更容易排到首位。" },
  { name: "V2", title: "Hybrid + Reranker", hit: "85.7%", recall: "100%", refusal: "100%", latency: "9.5 s", note: "融合关键词与向量召回，再将排序和证据充分性拆开，最终兼顾命中与拒答。", winner: true },
];

export const metadata = {
  title: "Recall Case Study — 从检索到可信回答",
  description: "Recall 个人知识库 RAG 的产品设计、V0/V1/V2 评测、Bad Case 与关键取舍。",
};

export default function CaseStudy() {
  return (
    <main className="case-page">
      <nav className="nav shell case-nav">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>Recall</span></Link>
        <div className="case-nav-actions">
          <a href="https://github.com/nbrhyq/Recall_RAG" target="_blank" rel="noreferrer"><Github size={16} /> GitHub</a>
          <Link className="button dark small" href="/"><ArrowLeft size={16} /> 返回 Demo</Link>
        </div>
      </nav>

      <header className="case-hero shell">
        <div className="case-kicker"><Sparkles size={14} /> PORTFOLIO CASE STUDY</div>
        <h1>让“我好像看过”，<br /><em>变成可验证的答案。</em></h1>
        <p>Recall 是一个本地优先的个人文档 RAG 产品。它不追求回答所有问题，而是让用户能够回到原始证据，并在知识不足时得到诚实拒答。</p>
        <div className="case-meta">
          <div><span>ROLE</span><b>AI 产品设计 · 全栈实现 · 评测</b></div>
          <div><span>SCOPE</span><b>PDF / 图片 / 文字知识库</b></div>
          <div><span>STACK</span><b>Qwen3 · Qdrant · SQLite</b></div>
        </div>
      </header>

      <section className="case-section shell problem-grid">
        <div>
          <div className="section-kicker">01 · PROBLEM</div>
          <h2>用户缺的不是更多答案，<br />而是能信任的依据。</h2>
        </div>
        <div className="problem-copy">
          <p>课程资料、PDF 和截图不断积累，但真正要使用知识时，用户往往只记得“我看过”，无法找到原文。普通搜索依赖关键词，通用大模型又可能脱离用户资料生成答案。</p>
          <div className="problem-points">
            <div><FileSearch size={19} /><span>如何把多种格式低成本沉淀为可检索知识？</span></div>
            <div><ShieldCheck size={19} /><span>如何验证证据真的能够回答问题？</span></div>
            <div><CircleAlert size={19} /><span>证据不足时，如何避免模型编造？</span></div>
          </div>
        </div>
      </section>

      <section className="architecture-wrap">
        <div className="case-section shell">
          <div className="section-kicker">02 · SOLUTION</div>
          <div className="architecture-head"><h2>从资料进入，<br />到有据可查的回答。</h2><p>本地 Qwen3 负责分类、重排、证据判断与生成；SQLite 保存内容元数据，Qdrant Local 保存语义向量。</p></div>
          <div className="pipeline" aria-label="Recall RAG pipeline">
            <div><FileSearch /><b>Extract</b><span>PDF / OCR / Text</span></div><i>→</i>
            <div><Layers3 /><b>Chunk</b><span>保留 PDF 页码</span></div><i>→</i>
            <div><Database /><b>Retrieve</b><span>Keyword + Vector</span></div><i>→</i>
            <div><Sparkles /><b>Rerank</b><span>Qwen3 二阶段排序</span></div><i>→</i>
            <div><ShieldCheck /><b>Ground</b><span>回答或明确拒答</span></div>
          </div>
        </div>
      </section>

      <section className="case-section shell">
        <div className="section-kicker">03 · ITERATION</div>
        <div className="iteration-head"><h2>技术不是堆出来的，<br />而是被问题推出来的。</h2><p>使用同一组 45 个标注问题运行 V0、V1、V2，分别验证 Embedding、Hybrid Search、Reranker 和 evidence gate 带来的真实变化。</p></div>
        <div className="version-grid">
          {versions.map((item) => <article className={item.winner ? "version-card winner" : "version-card"} key={item.name}>
            <div className="version-title"><span>{item.name}</span><h3>{item.title}</h3>{item.winner && <b><Check size={13} /> Final</b>}</div>
            <div className="version-metrics"><div><small>Hit@1</small><strong>{item.hit}</strong></div><div><small>Hit@5</small><strong>{item.recall}</strong></div><div><small>拒答</small><strong>{item.refusal}</strong></div><div><small>延迟</small><strong>{item.latency}</strong></div></div>
            <p>{item.note}</p>
          </article>)}
        </div>
      </section>

      <section className="case-section shell bad-cases">
        <div className="section-kicker">04 · BAD CASES</div>
        <h2>三个失败，改变了最终方案。</h2>
        <div className="bad-case-list">
          <article><span>01</span><div><h3>语义相关，不等于能够回答</h3><p>Embedding 把正确页面带进 Top 5，却让同主题的宽泛片段排在首位。因此加入 Hybrid 候选与二阶段重排，而不是把向量相似度当作最终答案。</p></div></article>
          <article><span>02</span><div><h3>“选出最好”会诱导模型错误放行</h3><p>小模型同时做排序和充分性判断时，对 10 个知识库外问题全部回答。最终把 ranking 与 answerability 拆成两个独立任务。</p></div></article>
          <article><span>03</span><div><h3>严格拒答也会伤害可用性</h3><p>第一版 evidence gate 错拒 7 个有答案的问题。加入语义证据保护阈值后错误拒答降至 0，但明确记录阈值只对当前数据集有效。</p></div></article>
        </div>
      </section>

      <section className="tradeoff-wrap">
        <div className="case-section shell tradeoff-grid">
          <div><div className="section-kicker">05 · PRODUCT JUDGEMENT</div><h2>选择可信度，<br />也公开它的代价。</h2></div>
          <div><p>V2 把 Hit@3、Hit@5 和拒答准确率提升到 100%，但检索阶段平均延迟达到 9.5 秒。产品没有隐藏这项代价，而是在界面中解释召回、重排、核验和生成阶段。</p><p>当前结果来自一份 8 页 PDF 和同一批校准问题，因此它证明的是迭代方法，而不是通用生产质量。</p></div>
        </div>
      </section>

      <section className="case-section shell next-section">
        <div className="section-kicker">06 · NEXT</div>
        <h2>下一步，不是再加一个模型。</h2>
        <div className="next-grid">
          <div><b>01</b><span>扩展到 5–10 份文档和 100 个问题</span></div>
          <div><b>02</b><span>拆分 calibration 与 held-out test set</span></div>
          <div><b>03</b><span>增加 claim-level citation accuracy</span></div>
          <div><b>04</b><span>优化超时恢复、缓存与端到端测试</span></div>
        </div>
        <div className="case-cta"><div><span>EXPLORE THE PRODUCT</span><h3>现在体验 Recall 的静态产品 Demo</h3></div><Link className="button dark" href="/">打开 Demo <ArrowUpRight size={17} /></Link></div>
      </section>

      <footer className="shell"><div className="brand"><span className="brand-mark">R</span><span>Recall</span></div><p>Source-grounded AI product case study.</p><span>© 2026</span></footer>
    </main>
  );
}
