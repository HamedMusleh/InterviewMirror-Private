export interface JobDescriptionRequest {
  role: {
    title: string
    department: string
    employment_type: string
    location: string
  }
  job_summary: string
  responsibilities: string[]
  requirements: {
    skills: {
      required: string[]
      preferred: string[]
    }
    experience: {
      minimum_years: number
      level: string
    }
    education: string[]
    certifications: string[]
    languages: string[]
  }
  technical_stack: string[]
  soft_skills: string[]
  screening_settings: {
    passing_score: number
  }
}

export interface JobDescriptionResponse extends JobDescriptionRequest {
  job_id: string
}

export interface JobOpportunity {
  /*
   * How many candidates have applied.
   *
   * Used to decide whether deleting is available at all: a posting with
   * applications cannot be deleted, and the card says so up front rather
   * than letting the recruiter confirm a dialog that then fails.
   */
  application_count: number

  job_id: string
  title: string
  department: string
  employment_type: string
  location: string
  job_summary: string
  required_skills: string[]
  minimum_years: number
  experience_level: string
  status: string
}

const API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL}/api/job-description`

export async function createJobDescription(
  recruiterId: number,
  job: JobDescriptionRequest,
): Promise<JobDescriptionResponse> {
  const response = await fetch(
    `${API_BASE_URL}/process?recruiter_id=${encodeURIComponent(recruiterId)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(job),
    },
  )

  if (!response.ok) {
    throw new Error("Failed to create job description")
  }

  return response.json()
}

export type JobStatus = "draft" | "published" | "archived"

/**
 * Job postings, newest first.
 *
 * Candidates pass includeArchived=false so closed postings drop off their
 * board. Recruiters keep them: closing a job should not hide it from the
 * person who closed it.
 */
export async function getJobOpportunities(
  includeArchived = true,
): Promise<JobOpportunity[]> {
  const response = await fetch(
    `${API_BASE_URL}?include_archived=${includeArchived}`,
  )

  if (!response.ok) {
    throw new Error("Failed to load job opportunities")
  }

  return response.json()
}


/**
 * Raised when the API refuses a job operation for a reason worth showing.
 *
 * Deleting a job that candidates have applied to is the case this exists
 * for: the server explains how many applications are in the way, and that
 * sentence is far more useful to a recruiter than "something went wrong".
 */
export class JobApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "JobApiError"
    this.status = status
  }
}

async function detailFrom(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = await response.json()

    return typeof body?.detail === "string" ? body.detail : fallback
  } catch {
    return fallback
  }
}

export interface JobForEdit {
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
  passing_score: number
  status: string
}

/**
 * The recruiter's view of a posting, for loading it back into the form.
 *
 * Separate from the candidate-facing job endpoint because that one withholds
 * the passing score; a form that could not read it would reset the
 * recruiter's screening threshold to the default on every save.
 */
export async function getJobDescriptionForEdit(
  jobId: string,
): Promise<JobForEdit> {
  const response = await fetch(
    `${API_BASE_URL}/${encodeURIComponent(jobId)}`,
  )

  if (!response.ok) {
    throw new JobApiError(
      await detailFrom(response, "Failed to load this job."),
      response.status,
    )
  }

  return response.json()
}

export async function updateJobDescription(
  jobId: string,
  job: JobDescriptionRequest,
): Promise<JobDescriptionResponse> {
  const response = await fetch(
    `${API_BASE_URL}/${encodeURIComponent(jobId)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(job),
    },
  )

  if (!response.ok) {
    throw new JobApiError(
      await detailFrom(response, "Failed to update this job."),
      response.status,
    )
  }

  return response.json()
}

/**
 * Close a posting, or reopen it.
 *
 * Archiving is what a finished job needs and deleting cannot give it:
 * everything candidates have already put into it stays, while the posting
 * stops accepting applications and leaves the candidate board.
 */
export async function setJobStatus(
  jobId: string,
  status: JobStatus,
): Promise<JobForEdit> {
  const response = await fetch(
    `${API_BASE_URL}/${encodeURIComponent(jobId)}/status`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    },
  )

  if (!response.ok) {
    throw new JobApiError(
      await detailFrom(response, "Failed to change this job's status."),
      response.status,
    )
  }

  return response.json()
}

export async function deleteJobDescription(jobId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/${encodeURIComponent(jobId)}`,
    {
      method: "DELETE",
    },
  )

  if (!response.ok) {
    throw new JobApiError(
      await detailFrom(response, "Failed to delete this job."),
      response.status,
    )
  }
}
