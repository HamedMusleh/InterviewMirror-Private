import type { CandidateReportResponse } from "../types/candidateReportTypes";

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/interviews`;

interface BackendCandidateReport {
  candidate_evaluation_id: number;
  interview_id: number;
  overall_score: number;
  skill_scores: Record<string, number>;
  summary: string;
  strengths: string[];
  areas_for_improvement: string[];
  recommendation: string;
  report_id: number;
  candidate_id: number;
  candidate_name: string;
  job_title: string;
  email: string;
  phone: string | null;
}

function mapCandidateReport(data: BackendCandidateReport): CandidateReportResponse {
  return {
    report_id: data.report_id,
    candidate_id: data.candidate_id,
    interview_id: data.interview_id,
    job_title: data.job_title,
    candidate_name: data.candidate_name,
    email: data.email,
    phone: data.phone,
    overall_score: data.overall_score,
    skill_scores: data.skill_scores,
    summary: data.summary,
    strengths: data.strengths,
    areas_for_improvement: data.areas_for_improvement,
    recommendation: data.recommendation,
  };
}

export async function getCandidateReport(
  interviewId: number
): Promise<CandidateReportResponse | null> {
  const response = await fetch(`${API_BASE_URL}/${interviewId}/report`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Failed to fetch candidate report");
  }

  const data: BackendCandidateReport = await response.json();
  return mapCandidateReport(data);
}