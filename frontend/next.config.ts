import type { NextConfig } from "next";

const ec2Origin = process.env.BACKEND_ORIGIN || "http://13.217.24.76:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/health", destination: `${ec2Origin}/health` },
      { source: "/check", destination: `${ec2Origin}/check` },
      { source: "/analyze_pdf", destination: `${ec2Origin}/analyze_pdf` },
      { source: "/analyze_image", destination: `${ec2Origin}/analyze_image` },
      { source: "/translate_report", destination: `${ec2Origin}/translate_report` },
      { source: "/progress/:path*", destination: `${ec2Origin}/progress/:path*` }
    ];
  }
};

export default nextConfig;
