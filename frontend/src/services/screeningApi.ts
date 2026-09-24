import {
  CategoryEvaluationStatus,
  ScoreCategory,
  ScreeningStatus,
} from '../types/screeningTypes'
import type {
  CandidateScreeningDetail,
  CandidateSummary,
  CategoryScore,
  MatchingResults,
  ScoringResponse,
} from '../types/screeningTypes'

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/screening`

type BackendStatus = 'recommended' | 'not_recommended'
type BackendCategoryStatus = 'evaluated' | 'not_applicable'

interface BackendScreeningResultSummary {
  application_id: number
  candidate_id: string
  name: string
  overall_score: number
  status: BackendStatus
  job_title: string
}

interface BackendCategoryBreakdownEntry {
  score: number | null
  weight: number | null
  weighted_score: number | null
  status: BackendCategoryStatus
}

interface BackendScreeningResultDetail {
  application_id: number
  criteria_id: number
  candidate_id: string
  candidate_name: string
  job_id: string
  job_title: string
  overall_score: number
  passing_score: number
  confidence_score: number | null
  final_status: BackendStatus
  category_breakdown: Record<string, BackendCategoryBreakdownEntry>
  matched_criteria: string[]
  missing_criteria: string[]
  matching_details: Record<string, unknown>
}

function mapStatus(status: BackendStatus): ScreeningStatus {
  return status === 'recommended'
    ? ScreeningStatus.Recommended
    : ScreeningStatus.Rejected
}

function mapCategoryStatus(
  status: BackendCategoryStatus,
): CategoryEvaluationStatus {
  return status === 'evaluated'
    ? CategoryEvaluationStatus.Evaluated
    : CategoryEvaluationStatus.NotEvaluated
}

function mapCategoryBreakdown(
  breakdown: Record<string, BackendCategoryBreakdownEntry>,
): Record<ScoreCategory, CategoryScore> {
  const result = {} as Record<ScoreCategory, CategoryScore>

  for (const category of Object.values(ScoreCategory)) {
    const entry = breakdown[category]

    result[category] = {
      score: entry?.score ?? 0,
      weight: entry?.weight ?? 0,
      weighted_score: entry?.weighted_score ?? 0,
      status: mapCategoryStatus(entry?.status ?? 'not_applicable'),
    }
  }

  return result
}

export async function getScreeningResults(
  jobId: string,
): Promise<CandidateSummary[]> {
  const response = await fetch(
    `${API_BASE_URL}/results/${encodeURIComponent(jobId)}`,
  )

  if (!response.ok) {
    throw new Error('Failed to fetch screening results')
  }

  const data: BackendScreeningResultSummary[] = await response.json()

  return data.map((item) => ({
    applicationId: String(item.application_id),
    jobId,
    jobTitle: item.job_title,
    name: item.name,
    overallScore: item.overall_score,
    status: mapStatus(item.status),
  }))
}

export async function getScreeningResultDetail(
  applicationId: string,
): Promise<CandidateScreeningDetail> {
  const response = await fetch(
    `${API_BASE_URL}/results/application/${encodeURIComponent(applicationId)}`,
  )

  if (!response.ok) {
    throw new Error('Failed to fetch screening result detail')
  }

  const data: BackendScreeningResultDetail = await response.json()

  const scoring: ScoringResponse = {
    candidate_id: data.candidate_id,
    job_id: data.job_id,
    category_breakdown: mapCategoryBreakdown(data.category_breakdown),
    overall_score: data.overall_score,
    passing_score: data.passing_score,
    final_status: mapStatus(data.final_status),
  }

  return {
    applicationId: String(data.application_id),
    jobId: data.job_id,
    name: data.candidate_name,
    matching: data.matching_details as unknown as MatchingResults,
    scoring,
  }
}