/** @type {import('next').NextConfig} */
const staticExport = process.env.STATIC_EXPORT === "true";
const repository = process.env.GITHUB_REPOSITORY?.split("/")[1] || "Recall_RAG";
const basePath = staticExport ? `/${repository}` : "";

const nextConfig = {
  reactStrictMode: true,
  ...(staticExport ? { output: "export", trailingSlash: true, basePath, assetPrefix: basePath } : {}),
  ...(!staticExport ? {
    async rewrites() {
      return [
        {
          source: "/backend/:path*",
          destination: `${process.env.API_INTERNAL_URL || "http://127.0.0.1:8000"}/:path*`,
        },
      ];
    },
  } : {}),
};

export default nextConfig;
