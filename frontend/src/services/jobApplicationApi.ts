// Full candidate-visible job description, as returned by
// GET /api/job-opportunities/{job_id}
// (see backend/app/schemas/job_opportunity.py::JobOpportunityResponse).
//
// Every field below always comes back from the backend (list fields
// default to `[]` rather than being omitted), so consumers decide for
// themselves whether a section has anything worth rendering -- see
// JobDescriptionDetails, which only renders sections that have a
// value. `id` is a database identifier, but it is kept here (and is
// not itself displayed to the candidate) because the existing
// application-submission flow below needs it as
// `job_opportunity_id`.
export interface JobOpportunityResponse {
  id: number
  job_id: string
  title: string
  department: string
  employment_type: string
  location: string
  job_summary: string
  responsibilities: string[]
  required_skills: string[]
  preferred_skills: string[]
  minimum_years: number
  experience_level: string
  education: string[]
  certifications: string[]
  languages: string[]
  technical_stack: string[]
  soft_skills: string[]

  /*
   * Whether this posting still takes applications.
   *
   * A fact rather than the posting's status: which of draft, published or
   * archived it sits in is the recruiter's workflow. This is the part a
   * candidate needs, so that a closed job says so instead of refusing a
   * form they have already filled in.
   */
  accepting_applications: boolean
}

export interface ApplicationSubmitResponse {
  application_id: number
  job_opportunity_id: number
  resume_id: number
  status: string
  applied_at: string
  // Only set once a real Interview record exists for this submission
  // (i.e. screening recommended this candidate). Never fabricated on
  // the frontend -- see ApplicationStatusResponse.interview_id below,
  // which is what CandidateApplicationPanel actually renders "Join
  // Interview" from.
  interview_id: number | null
}

// Mirrors ApplicationPageState in
// backend/app/schemas/application_status.py, the backend's single
// source of truth for this derived state.
export type ApplicationPageState =
  | "job_not_ready"
  | "can_apply"
  | "screening_in_progress"
  | "approved_for_interview"
  | "rejected"
  | "evaluation_in_progress"

export interface ApplicationStatusResponse {
  state: ApplicationPageState
  application_id: number | null
  interview_id: number | null
}

interface ApiErrorBody {
  detail?: string
}

export class JobApplicationApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "JobApplicationApiError"
    this.status = status
  }
}

// Mirrors ALLOWED_RESUME_CONTENT_TYPES / MAX_RESUME_FILE_SIZE_BYTES in
// backend/app/core/resume_validation.py, the backend's single source
// of truth for resume validation. Keep these in sync with that file.
export const ALLOWED_RESUME_CONTENT_TYPES = [
  "application/pdf",
]
export const MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// NOTE: There is intentionally no localStorage-based "remembered
// candidate" mechanism here (there used to be a `candidateEmail` key
// stored in the browser). That approach broke as soon as a second
// candidate used the same browser: the page would silently assume
// they were whoever last applied. Candidate identity for both
// checking status and applying now always comes from an email the
// candidate explicitly types into CandidateApplicationPanel for that
// action -- never from anything persisted automatically. See
// getApplicationStatus/submitApplication below, both of which require
// the caller to pass an email rather than reading one from storage.

async function extractErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body: ApiErrorBody = await response.json()

    if (body && typeof body.detail === "string" && body.detail.trim()) {
      return body.detail
    }
  } catch {
    // Response body wasn't JSON (or was empty) — fall back below.
  }

  return fallback
}

export async function getJobOpportunity(
  jobId: string,
): Promise<JobOpportunityResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/job-opportunities/${encodeURIComponent(jobId)}`,
  )

  if (!response.ok) {
    throw new JobApplicationApiError(
      await extractErrorMessage(response, "Failed to load this job."),
      response.status,
    )
  }

  return response.json()
}

export async function getApplicationStatus(params: {
  jobId: string
  // Optional on purpose: omitting it asks the backend for the job's
  // own readiness only ("job_not_ready" vs "can_apply"), without
  // resolving -- or assuming -- any candidate. A specific candidate's
  // status is only ever looked up once they explicitly type their
  // email into CandidateApplicationPanel for that action.
  email?: string
}): Promise<ApplicationStatusResponse> {
  const query = new URLSearchParams({ job_id: params.jobId })

  if (params.email) {
    query.set("email", params.email)
  }

  const response = await fetch(
    `${API_BASE_URL}/api/applications/status?${query.toString()}`,
  )

  if (!response.ok) {
    throw new JobApplicationApiError(
      await extractErrorMessage(
        response,
        "Failed to load this job's application status.",
      ),
      response.status,
    )
  }

  return response.json()
}

export async function submitApplication(params: {
  jobOpportunityId: number
  firstName: string
  lastName: string
  email: string
  phone: string
  resume: File
}): Promise<ApplicationSubmitResponse> {
  const formData = new FormData()

  formData.append("job_opportunity_id", String(params.jobOpportunityId))
  // There is no login/registration flow yet: the backend finds or
  // creates the candidate's User/Candidate record from this email,
  // the temporary identity mechanism until real authentication
  // exists. candidate_id is never sent from here.
  formData.append("first_name", params.firstName)
  formData.append("last_name", params.lastName)
  formData.append("email", params.email)
  formData.append("phone", params.phone)
  formData.append("file", params.resume)

  const response = await fetch(`${API_BASE_URL}/api/applications`, {
    method: "POST",
    // No Content-Type header: the browser sets the multipart
    // boundary automatically when the body is a FormData instance.
    body: formData,
  })

  if (!response.ok) {
    throw new JobApplicationApiError(
      await extractErrorMessage(
        response,
        "Failed to submit your application. Please try again.",
      ),
      response.status,
    )
  }

  return response.json()
}
