import path from "node:path";
import type { NextConfig } from "next";

const repositoryRoot = path.resolve(__dirname, "../..");

const nextConfig: NextConfig = {
  outputFileTracingRoot: repositoryRoot,
  turbopack: {
    root: repositoryRoot,
  },
};

export default nextConfig;
