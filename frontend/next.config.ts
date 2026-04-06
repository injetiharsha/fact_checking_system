import type { NextConfig } from "next";

const rawOrigin = process.env.BACKEND_ORIGIN || "http://13.217.24.76:8000";
const ec2Origin = rawOrigin.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/backend/:path*", destination: `${ec2Origin}/:path*` },
      ],
    };
  },
};

export default nextConfig;
