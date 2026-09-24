from uuid import uuid4

from app.schemas.job_description import (
    Experience,
    JobDescriptionRequest,
    JobDescriptionResponse,
    Requirements,
    Skills,
)


class JobDescriptionService:

    def process_job_description(
        self,
        request: JobDescriptionRequest,
    ) -> JobDescriptionResponse:
        """
        Validate and transform structured recruiter input
        into the standardized job description JSON.
        """

        job_id = f"JD-{uuid4().hex[:8].upper()}"

        cleaned_requirements = Requirements(
            skills=Skills(
                required=self._clean_list(
                    request.requirements.skills.required
                ),
                preferred=self._clean_list(
                    request.requirements.skills.preferred
                ),
            ),
            experience=Experience(
                minimum_years=(
                    request.requirements.experience.minimum_years
                ),
                level=request.requirements.experience.level.strip(),
            ),
            education=self._clean_list(
                request.requirements.education
            ),
            certifications=self._clean_list(
                request.requirements.certifications
            ),
            languages=self._clean_list(
                request.requirements.languages
            ),
        )

        return JobDescriptionResponse(
            job_id=job_id,
            role=request.role,
            job_summary=request.job_summary.strip(),
            responsibilities=self._clean_list(
                request.responsibilities
            ),
            requirements=cleaned_requirements,
            technical_stack=self._clean_list(
                request.technical_stack
            ),
            soft_skills=self._clean_list(
                request.soft_skills
            ),
            screening_settings=request.screening_settings,
        )

    @staticmethod
    def _clean_list(values: list[str]) -> list[str]:
        """
        Remove empty values, spaces and duplicates
        while preserving the original order.
        """
        cleaned_values: list[str] = []
        seen_values: set[str] = set()

        for value in values:
            cleaned_value = value.strip()

            if not cleaned_value:
                continue

            normalized_value = cleaned_value.lower()

            if normalized_value not in seen_values:
                cleaned_values.append(cleaned_value)
                seen_values.add(normalized_value)

        return cleaned_values