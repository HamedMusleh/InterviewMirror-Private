from typing import List

from pydantic import BaseModel, ConfigDict


class JobOpportunityResponse(BaseModel):
    """Candidate-facing view of a job opportunity, used by the Job
    Details page (both the recruiter's read-only view and the
    candidate's view -- see JobDescriptionDetails on the frontend).

    Includes every candidate-visible job-description field stored on
    JobOpportunity. Deliberately excludes recruiter-only /
    internal-screening fields (recruiter_id, passing_score, status)
    that a candidate has no business seeing.

    `id` is kept even though it is a database identifier because the
    existing candidate-facing submission flow
    (POST /api/applications, see jobApplicationApi.ts) already relies
    on it as `job_opportunity_id` -- removing it would break
    submission, not just hide an implementation detail.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    title: str
    department: str
    employment_type: str
    location: str
    job_summary: str
    responsibilities: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    minimum_years: int
    experience_level: str
    education: List[str]
    certifications: List[str]
    languages: List[str]
    technical_stack: List[str]
    soft_skills: List[str]

    # Whether this posting still takes applications.
    #
    # Deliberately a fact rather than the status itself. Which of draft,
    # published or archived a posting sits in is the recruiter's workflow
    # and none of a candidate's business -- there is a test asserting
    # status never reaches this response. What a candidate does need is
    # the one thing that state implies for them, so that they are told a
    # job is closed rather than discovering it when the form they just
    # filled in is refused.
    accepting_applications: bool
