export interface ReportListItem {
  report_id: number;
  candidate_id: number;
  interview_id: number;
  candidate_name: string;
  job_title: string;
  overall_score: number;
}
 
export type ReportsListViewState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "success"; data: ReportListItem[] };