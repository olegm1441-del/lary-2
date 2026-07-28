import path from "node:path";
import type { NextConfig } from "next";

const applicationRoot = path.resolve(__dirname);

const nextConfig: NextConfig = {
  outputFileTracingRoot: applicationRoot,
  turbopack: {
    root: applicationRoot,
  },
};

export default nextConfig;
