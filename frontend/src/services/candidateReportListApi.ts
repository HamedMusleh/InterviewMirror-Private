import type { ReportListItem } from "../types/reportsListTypes";

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/reports`;

interface BackendReportSummary {
  report_id: number;
  candidate_id: number;
  interview_id: number;
  candidate_name: string;
  job_title: string;
  overall_score: number;
}

function mapReportSummary(data: BackendReportSummary): ReportListItem {
  return {
    report_id: data.report_id,
    candidate_id: data.candidate_id,
    interview_id: data.interview_id,
    candidate_name: data.candidate_name,
    job_title: data.job_title,
    overall_score: data.overall_score,
  };
}

export async function getAllReports(): Promise<ReportListItem[]> {
  const response = await fetch(API_BASE_URL);

  if (!response.ok) {
    throw new Error("Failed to fetch candidate reports");
  }

  const data: BackendReportSummary[] = await response.json();
  return data.map(mapReportSummary);
}