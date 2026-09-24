export interface CandidateReportResponse {
  report_id: number;
  candidate_id: number;
  interview_id: number;
  job_title: string;
  candidate_name: string;
  email: string;
  phone: string | null;
  overall_score: number;
  skill_scores: Record<string, number>;
  summary: string;
  strengths: string[];
  areas_for_improvement: string[];
  recommendation: string;
}

export type CandidateReportViewState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "not_found" }
  | { status: "success"; data: CandidateReportResponse };