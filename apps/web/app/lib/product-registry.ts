import contestsData from "../../../../config/product/contests.json";
import modulesData from "../../../../config/product/modules.json";
import profilesData from "../../../../config/product/module-contest-profiles.json";
import examplesData from "../../../../config/product/examples-manifest.json";

export type Contest = {
  slug: string;
  name: string;
  short_name: string;
  status: "active" | "preparing" | "hidden";
};

export type ProductModule = {
  slug: string;
  status: "active" | "preparing" | "hidden";
  category: string;
  title: string;
  promise: string;
  duration: string;
  output_formats: string[];
  feature_flags: Record<string, boolean>;
};

export type ModuleContestProfile = {
  module_slug: string;
  contest_slug: string;
  status: "ready" | "preparing" | "disabled";
  card_visibility: "visible" | "hidden";
  example_pack_id: string | null;
  profile_version: string | null;
};

export const publicContests = contestsData as Contest[];
export const publicModules = modulesData as ProductModule[];
export const moduleContestProfiles = profilesData as ModuleContestProfile[];

export function getPublicContests() {
  return publicContests.filter((contest) => contest.status !== "hidden");
}

export function getPublicModules() {
  return publicModules.filter((module) => module.status !== "hidden");
}

export function getModuleProfile(moduleSlug: string, contestSlug: string) {
  return moduleContestProfiles.find(
    (profile) => profile.module_slug === moduleSlug && profile.contest_slug === contestSlug,
  );
}

export function getSupportedContests(moduleSlug: string) {
  const visible = new Set(
    moduleContestProfiles
      .filter((profile) => profile.module_slug === moduleSlug && profile.card_visibility === "visible")
      .map((profile) => profile.contest_slug),
  );
  return getPublicContests().filter((contest) => visible.has(contest.slug));
}

export function hasRealExample(moduleSlug: string, contestSlug: string) {
  const profile = getModuleProfile(moduleSlug, contestSlug);
  if (!profile?.example_pack_id) return false;
  return examplesData.some(
    (item) =>
      item.example_pack_id === profile.example_pack_id &&
      item.module_slug === moduleSlug &&
      item.contest_slug === contestSlug &&
      item.migration_status === "legacy_preview",
  );
}

