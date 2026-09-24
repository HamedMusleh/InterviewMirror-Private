from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.repositories.candidate_report_repository import (
    CandidateReportRepository,
)
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.candidate_report import (
    CandidateReport,
    CandidateReportResponse,
    CandidateReportSummary,
)


def _score_out_of_100(score: float) -> float:
    normalized = score * 10 if score <= 10 else score
    return max(0.0, min(100.0, round(normalized, 2)))


def _scores_out_of_100(scores: dict[str, float]) -> dict[str, float]:
    return {
        skill: _score_out_of_100(value)
        for skill, value in scores.items()
    }


class CandidateReportHandlerError(Exception):
    """Base class for candidate report storage/link/API failures."""


class InterviewNotFoundError(CandidateReportHandlerError):
    """
    Raised when interview_id does not refer to a usable Interview -
    either the Interview itself does not exist, or the Application /
    JobOpportunity it links to is missing.
    """


class CandidateNotFoundError(CandidateReportHandlerError):
    """
    Raised when the Candidate linked to the interview's Application
    does not exist, or that Candidate's User does not exist.
    """


class CandidateEvaluationNotFoundError(CandidateReportHandlerError):
    """
    Raised when candidate_evaluation_id does not refer to an existing
    CandidateEvaluation (store), or an interview has no CandidateEvaluation
    yet (get - Evaluation has not finished this interview).
    """


class CandidateReportRelationshipError(CandidateReportHandlerError):
    """
    Raised when the report being stored does not belong together -
    the request path's interview_id does not match the report body's
    interview_id, or the CandidateEvaluation referenced by
    candidate_evaluation_id does not actually belong to that
    interview_id (see CandidateReportHandler.store_report).
    """


class CandidateReportAlreadyExistsError(CandidateReportHandlerError):
    """
    Raised when a CandidateReport has already been stored for this
    candidate_evaluation_id - candidate_evaluation_id is unique on
    candidate_reports, one final report per evaluation.
    """


class CandidateReportNotFoundError(CandidateReportHandlerError):
    """Raised when no CandidateReport has been stored for an interview yet."""


class CandidateReportHandler:
    """
    Handler for the "store + link + retrieve Candidate Report" use case.

    Does not generate report content and does not call an LLM - it only
    validates, persists, and re-assembles the already-generated
    CandidateReport. overall_score / skill_scores
    are always read from CandidateEvaluation (via
    CandidateEvaluationRepository), never from the request body, since
    candidate_evaluations is their single source of truth.
    """

    def __init__(
        self,
        candidate_report_repository: CandidateReportRepository,
        candidate_evaluation_repository: CandidateEvaluationRepository,
        interview_repository: InterviewRepository,
        application_repository: ApplicationRepository,
        candidate_repository: CandidateRepository,
        user_repository: UserRepository,
        job_opportunity_repository: JobOpportunityRepository,
    ) -> None:
        self.candidate_report_repository = candidate_report_repository
        self.candidate_evaluation_repository = (
            candidate_evaluation_repository
        )
        self.interview_repository = interview_repository
        self.application_repository = application_repository
        self.candidate_repository = candidate_repository
        self.user_repository = user_repository
        self.job_opportunity_repository = job_opportunity_repository

    def store_report(
        self,
        interview_id: int,
        report: CandidateReport,
    ) -> CandidateReportResponse:
        if report.interview_id != interview_id:
            raise CandidateReportRelationshipError(
                f"Report interview_id={report.interview_id} does not "
                f"match interview {interview_id}."
            )

        candidate, user, job = self._resolve_context(interview_id)

        candidate_evaluation = (
            self.candidate_evaluation_repository.get_by_id(
                report.candidate_evaluation_id
            )
        )
        if candidate_evaluation is None:
            raise CandidateEvaluationNotFoundError(
                "Candidate evaluation "
                f"{report.candidate_evaluation_id} was not found."
            )

        # verify interview_id actually belongs to this CandidateEvaluation.
        if candidate_evaluation.interview_id != interview_id:
            raise CandidateReportRelationshipError(
                f"Candidate evaluation {candidate_evaluation.id} belongs "
                f"to interview {candidate_evaluation.interview_id}, not "
                f"interview {interview_id}."
            )

        if report.overall_score != candidate_evaluation.overall_score:
            raise CandidateReportRelationshipError(
                "Report overall_score does not match the stored "
                "candidate evaluation."
            )

        if report.skill_scores != candidate_evaluation.skill_scores:
            raise CandidateReportRelationshipError(
                "Report skill_scores do not match the stored "
                "candidate evaluation."
            )

        if self.candidate_report_repository.get_by_candidate_evaluation_id(
            candidate_evaluation.id
        ) is not None:
            raise CandidateReportAlreadyExistsError(
                "A candidate report already exists for candidate "
                f"evaluation {candidate_evaluation.id}."
            )

        saved = self.candidate_report_repository.save(report)

        return CandidateReportResponse(
            report_id=saved.id,
            candidate_evaluation_id=candidate_evaluation.id,
            candidate_id=candidate.id,
            interview_id=interview_id,
            job_title=job.title,
            candidate_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            phone=candidate.phone,
            overall_score=_score_out_of_100(
                candidate_evaluation.overall_score,
            ),
            skill_scores=_scores_out_of_100(
                candidate_evaluation.skill_scores,
            ),
            summary=saved.summary,
            strengths=saved.strengths,
            areas_for_improvement=saved.areas_for_improvement,
            recommendation=saved.recommendation,
        )

    def get_report(self, interview_id: int) -> CandidateReportResponse:
        candidate, user, job = self._resolve_context(interview_id)

        candidate_evaluation = (
            self.candidate_evaluation_repository.get_by_interview_id(
                interview_id
            )
        )
        if candidate_evaluation is None:
            raise CandidateEvaluationNotFoundError(
                f"No candidate evaluation exists yet for interview "
                f"{interview_id}."
            )

        report = (
            self.candidate_report_repository.get_by_candidate_evaluation_id(
                candidate_evaluation.id
            )
        )
        if report is None:
            raise CandidateReportNotFoundError(
                f"Candidate report for interview {interview_id} was not "
                "found."
            )

        return CandidateReportResponse(
            report_id=report.id,
            candidate_evaluation_id=candidate_evaluation.id,
            candidate_id=candidate.id,
            interview_id=interview_id,
            job_title=job.title,
            candidate_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            phone=candidate.phone,
            overall_score=_score_out_of_100(
                candidate_evaluation.overall_score,
            ),
            skill_scores=_scores_out_of_100(
                candidate_evaluation.skill_scores,
            ),
            summary=report.summary,
            strengths=report.strengths,
            areas_for_improvement=report.areas_for_improvement,
            recommendation=report.recommendation,
        )

    def list_reports(self) -> list[CandidateReportSummary]:

        reports = self.candidate_report_repository.list_all()

        summaries: list[CandidateReportSummary] = []

        for report in reports:
            candidate_evaluation = (
                self.candidate_evaluation_repository.get_by_id(
                    report.candidate_evaluation_id
                )
            )
            if candidate_evaluation is None:
                continue

            try:
                candidate, user, job = self._resolve_context(
                    candidate_evaluation.interview_id
                )
            except CandidateReportHandlerError:
                continue

            summaries.append(
                CandidateReportSummary(
                    report_id=report.id,
                    candidate_id=candidate.id,
                    interview_id=candidate_evaluation.interview_id,
                    candidate_name=f"{user.first_name} {user.last_name}",
                    job_title=job.title,
                    overall_score=_score_out_of_100(
                        candidate_evaluation.overall_score,
                    ),
                )
            )

        return summaries

    def _resolve_context(self, interview_id: int):
        """
        Walk Interview -> Application -> Candidate -> User and
        Application -> JobOpportunity, raising the appropriate
        NotFoundError the moment a link is missing.

        Returns (candidate, user, job).
        """

        interview = self.interview_repository.get_by_id(interview_id)
        if interview is None:
            raise InterviewNotFoundError(
                f"Interview {interview_id} was not found."
            )

        application = self.application_repository.get_by_id(
            interview.application_id
        )
        if application is None:
            raise InterviewNotFoundError(
                f"Application for interview {interview_id} was not found."
            )

        candidate = self.candidate_repository.get_by_id(
            application.candidate_id
        )
        if candidate is None:
            raise CandidateNotFoundError(
                f"Candidate for interview {interview_id} was not found."
            )

        user = self.user_repository.get_by_id(candidate.user_id)
        if user is None:
            raise CandidateNotFoundError(
                f"User for candidate {candidate.id} was not found."
            )

        job = self.job_opportunity_repository.get_by_id(
            application.job_opportunity_id
        )
        if job is None:
            raise InterviewNotFoundError(
                f"Job opportunity for interview {interview_id} was not "
                "found."
            )

        return candidate, user, job