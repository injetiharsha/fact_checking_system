import type { NextConfig } from "next";
import path from "node:path";

const rawOrigin = process.env.BACKEND_ORIGIN || "http://13.217.24.76:8000";
const ec2Origin = rawOrigin.replace(/\/+$/, ""); // remove trailing slash

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    return {
      beforeFiles: [
        // Preferred: call backend through /backend/*
        { source: "/backend/:path*", destination: `${ec2Origin}/:path*` },

        // Backward compatibility for existing frontend calls
        { source: "/health", destination: `${ec2Origin}/health` },
        { source: "/check", destination: `${ec2Origin}/check` },
        { source: "/analyze_pdf", destination: `${ec2Origin}/analyze_pdf` },
        { source: "/analyze_image", destination: `${ec2Origin}/analyze_image` },
        { source: "/translate_report", destination: `${ec2Origin}/translate_report` },
        { source: "/progress/:path*", destination: `${ec2Origin}/progress/:path*` },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
