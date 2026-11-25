// API_URL is read at BUILD time (rewrites are baked into the standalone build).
import path from "node:path";
import { fileURLToPath } from "node:url";

const API = process.env.API_URL || "http://localhost:8000";
const here = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.VERCEL ? undefined : "standalone",
  eslint: { ignoreDuringBuilds: true },
  webpack(config) {
    config.resolve.alias["@"] = path.join(here, "src");
    return config;
  },
  async redirects() {
    return [{ source: "/", destination: "/fa", permanent: false }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;