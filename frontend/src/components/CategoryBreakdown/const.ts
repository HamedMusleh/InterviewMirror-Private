import { ScoreCategory } from "../../types/screeningTypes";

export const CATEGORY_LABELS: Record<ScoreCategory, string> = {
  [ScoreCategory.Skills]: "Skills",
  [ScoreCategory.Experience]: "Experience",
  [ScoreCategory.Education]: "Education",
  [ScoreCategory.Projects]: "Projects",
  [ScoreCategory.Certifications]: "Certifications",
  [ScoreCategory.Languages]: "Languages",
  [ScoreCategory.SoftSkills]: "Soft Skills",
};

export const CATEGORY_ORDER: readonly ScoreCategory[] = [
  ScoreCategory.Skills,
  ScoreCategory.Experience,
  ScoreCategory.Education,
  ScoreCategory.Projects,
  ScoreCategory.Certifications,
  ScoreCategory.Languages,
  ScoreCategory.SoftSkills,
];
