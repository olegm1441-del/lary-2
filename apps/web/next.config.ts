import path from "node:path";
import type { NextConfig } from "next";
import { getBuildSha } from "./app/lib/build-info";

const applicationRoot = path.resolve(__dirname);

const nextConfig: NextConfig = {
  outputFileTracingRoot: applicationRoot,
  turbopack: {
    root: applicationRoot,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Lari-Build-Sha", value: getBuildSha() },
          { key: "Cache-Control", value: "no-store, max-age=0, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
