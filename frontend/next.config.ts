import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Voice transcription on a small CPU can take longer than the
    // default 30 seconds; don't let the proxy give up first.
    proxyTimeout: 180_000,
  },
  async rewrites() {
    return [
      {
        // Anything the browser requests at /api/* is forwarded by
        // Next.js (server-side) to the backend. Because the browser
        // only ever talks to its own origin, CORS never applies.
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;