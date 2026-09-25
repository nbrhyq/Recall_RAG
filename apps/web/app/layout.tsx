import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/newsreader/500.css";
import "./styles.css";
import "./pdf.css";

export const metadata = {
  title: "Recall — 本地 PDF 知识库",
  description: "A private, source-grounded PDF knowledge assistant powered by local Qwen3.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
