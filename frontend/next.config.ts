import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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