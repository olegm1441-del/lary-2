export function getBuildSha() {
  return (
    process.env.RAILWAY_GIT_COMMIT_SHA ||
    process.env.GIT_COMMIT_SHA ||
    process.env.SOURCE_VERSION ||
    "local"
  ).trim();
}

export const buildSha = getBuildSha();
