export enum ScreeningStatus {
  Recommended = "recommended",
  Review = "review",
  Rejected = "rejected",
}

export enum ScoreTone {
  Good = "good",
  Warning = "warning",
  Bad = "bad",
}

export enum ScoreCategory {
  Skills = "skills",
  Experience = "experience",
  Education = "education",
  Projects = "projects",
  Certifications = "certifications",
  Languages = "languages",
  SoftSkills = "soft_skills",
}

export enum CategoryEvaluationStatus {
  Evaluated = "evaluated",
  NotEvaluated = "not_evaluated",
}

export enum PillVariant {
  Matched = "matched",
  Missing = "missing",
}

export enum ScoreFilter {
  All = "all",
  High = "high",
  Medium = "medium",
  Low = "low",
}

export enum ScreeningStatusFilter {
  All = "all",
  Recommended = "recommended",
  Review = "review",
  Rejected = "rejected",
}

/** Row shown in the Screening Results table. */
export interface CandidateSummary {
  applicationId: string;
  jobId: string;
  name: string;
  overallScore: number;
  status: ScreeningStatus;
  jobTitle: string
}

export interface RequiredSkillMatch {
  required_skill: string;
  matched_skill: string | null;
  similarity_score: number;
  evidence: string | null;
}

export interface PreferredSkillMatch {
  preferred_skill: string;
  matched_skill: string | null;
  similarity_score: number;
  evidence: string | null;
}

export interface SkillsResult {
  score: number;
  required: RequiredSkillMatch[];
  preferred: PreferredSkillMatch[];
}

export interface ExperienceResult {
  score: number;
  candidate_years: number;
  required_years: number;
  level_match: boolean;
  evidence: string[];
}

export interface EducationResult {
  score: number;
  matched_field: string;
  evidence: string;
}

export interface ProjectMatch {
  project_name: string;
  matched_domain: string;
  similarity_score: number;
  evidence: string;
}

export interface ProjectsResult {
  score: number;
  matches: ProjectMatch[];
}

export interface CertificationsResult {
  score: number;
  matched: string[];
  missing: string[];
}

export interface LanguagesResult {
  score: number;
  matched: string[];
  missing: string[];
}

export interface SoftSkillsResult {
  score: number;
  matched: string[];
  missing: string[];
}

export interface MatchingResults {
  skills: SkillsResult;
  experience: ExperienceResult;
  education: EducationResult;
  projects: ProjectsResult;
  certifications: CertificationsResult;
  languages: LanguagesResult;
  soft_skills: SoftSkillsResult;
}

export interface MatchingResultsResponse {
  candidate_id: string;
  job_id: string;
  matching_results: MatchingResults;
}

export interface CategoryScore {
  score: number;
  weight: number;
  weighted_score: number;
  status: CategoryEvaluationStatus;
}

export interface ScoringResponse {
  candidate_id: string;
  job_id: string;
  category_breakdown: Record<ScoreCategory, CategoryScore>;
  overall_score: number;
  passing_score: number;
  final_status: ScreeningStatus;
}

/** Combined shape consumed by the candidate details page. */
export interface CandidateScreeningDetail {
  applicationId: string;
  jobId: string;
  name: string;
  matching: MatchingResults;
  scoring: ScoringResponse;
}
