from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.resume_matching import (
    EducationMatchingResult,
    ExperienceMatchingResult,
    ListMatchingResult,
    MatchingRequest,
    MatchingResponse,
    MatchingResults,
    PreferredSkillMatch,
    ProjectMatch,
    ProjectsMatchingResult,
    SkillMatch,
    SkillsMatchingResult,
)


MATCH_THRESHOLD = 70


@dataclass(frozen=True)
class EffectiveRequirements:
    """The requirements needed by the resume-matching evaluator."""

    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    minimum_years: float
    experience_level: str
    education: tuple[str, ...]
    projects_required: bool
    project_domains: tuple[str, ...]
    certifications: tuple[str, ...]
    languages: tuple[str, ...]
    soft_skills: tuple[str, ...]


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _score_or_zero(score: float | None) -> float:
    return 0 if score is None else score


def _not_applicable(result, **updates):
    return result.model_copy(
        update={"score": None, "status": "not_applicable", **updates}
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_list(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return tuple(cleaned)


def _skill_names(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()

    names: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("name")
        if isinstance(value, str):
            names.append(value)
    return _clean_list(names)


def _number(value: Any, default: float = 0) -> float:
    return value if isinstance(value, (int, float)) and value >= 0 else default


class ResumeMatchingService:
    """Normalizes model output into the resume-matching API contract."""

    def build_response(
        self,
        request: MatchingRequest,
        results: MatchingResults,
    ) -> MatchingResponse:
        requirements = self._resolve_requirements(request)
        normalized = self._normalize_results(results, requirements)
        return MatchingResponse(
            candidate_id=request.resume.candidate_id.strip(),
            job_id=request.screening_criteria["job_id"].strip(),
            matching_results=normalized,
        )

    @staticmethod
    def _resolve_requirements(request: MatchingRequest) -> EffectiveRequirements:
        criteria = _as_mapping(request.screening_criteria.get("screening_criteria"))
        job_requirements = request.job_description.requirements

        skills = _as_mapping(criteria.get("skills"))
        experience = _as_mapping(criteria.get("experience"))
        education = _as_mapping(criteria.get("education"))
        projects = _as_mapping(criteria.get("projects"))
        certifications = _as_mapping(criteria.get("certifications"))
        languages = _as_mapping(criteria.get("languages"))
        soft_skills = _as_mapping(criteria.get("soft_skills"))

        required_skills = _skill_names(skills.get("required"))
        if not required_skills:
            required_skills = _clean_list(job_requirements.skills.required)

        preferred_skills = _skill_names(skills.get("preferred"))
        if not preferred_skills:
            preferred_skills = _clean_list(job_requirements.skills.preferred)

        minimum_years = _number(experience.get("minimum_years")) or float(
            job_requirements.experience.minimum_years
        )
        experience_level = str(
            experience.get("level") or job_requirements.experience.level
        ).strip()

        education_fields = _clean_list(education.get("preferred_fields"))
        if not education_fields:
            education_fields = _clean_list(job_requirements.education)

        project_domains = _clean_list(projects.get("relevant_domains"))
        projects_required = projects.get("required") is True

        certification_names = _clean_list(certifications.get("criteria"))
        if not certification_names:
            certification_names = _clean_list(job_requirements.certifications)

        language_names = _clean_list(languages.get("criteria"))
        if not language_names:
            language_names = _clean_list(job_requirements.languages)

        soft_skill_names = _clean_list(soft_skills.get("criteria"))
        if not soft_skill_names:
            soft_skill_names = _clean_list(request.job_description.soft_skills)

        return EffectiveRequirements(
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            minimum_years=minimum_years,
            experience_level=experience_level,
            education=education_fields,
            projects_required=projects_required,
            project_domains=project_domains,
            certifications=certification_names,
            languages=language_names,
            soft_skills=soft_skill_names,
        )

    def _normalize_results(
        self,
        results: MatchingResults,
        requirements: EffectiveRequirements,
    ) -> MatchingResults:
        return results.model_copy(
            update={
                "skills": self._normalize_skills(results.skills, requirements),
                "experience": self._normalize_experience(
                    results.experience, requirements
                ),
                "projects": self._normalize_projects(results.projects, requirements),
                "education": self._normalize_education(
                    results.education, requirements
                ),
                "certifications": self._normalize_list_result(
                    results.certifications, requirements.certifications
                ),
                "languages": self._normalize_list_result(
                    results.languages, requirements.languages
                ),
                "soft_skills": self._normalize_list_result(
                    results.soft_skills, requirements.soft_skills
                ),
            }
        )

    def _normalize_skills(
        self,
        result: SkillsMatchingResult,
        requirements: EffectiveRequirements,
    ) -> SkillsMatchingResult:
        required_by_name = {
            _key(item.required_skill): item for item in result.required
        }
        preferred_by_name = {
            _key(item.preferred_skill): item for item in result.preferred
        }

        required = [
            self._skill_match(
                required_by_name.get(_key(name)),
                name,
                required=True,
            )
            for name in requirements.required_skills
        ]
        preferred = [
            self._skill_match(
                preferred_by_name.get(_key(name)),
                name,
                required=False,
            )
            for name in requirements.preferred_skills
        ]

        if not required and not preferred:
            return _not_applicable(result, required=[], preferred=[])

        return result.model_copy(
            update={
                "score": _score_or_zero(result.score),
                "status": "evaluated",
                "required": required,
                "preferred": preferred,
            }
        )

    @staticmethod
    def _skill_match(item, criterion_name: str, *, required: bool):
        if item is None:
            if required:
                return SkillMatch(
                    required_skill=criterion_name,
                    matched_skill=None,
                    similarity_score=0,
                    evidence=None,
                )
            return PreferredSkillMatch(
                preferred_skill=criterion_name,
                matched_skill=None,
                similarity_score=0,
                evidence=None,
            )

        matched = item.similarity_score >= MATCH_THRESHOLD
        common = {
            "matched_skill": item.matched_skill if matched else None,
            "similarity_score": item.similarity_score,
            "evidence": item.evidence if matched else None,
        }
        if required:
            return SkillMatch(required_skill=criterion_name, **common)
        return PreferredSkillMatch(preferred_skill=criterion_name, **common)

    @staticmethod
    def _normalize_experience(
        result: ExperienceMatchingResult,
        requirements: EffectiveRequirements,
    ) -> ExperienceMatchingResult:
        applicable = requirements.minimum_years > 0 or bool(
            requirements.experience_level
        )
        if not applicable:
            return _not_applicable(
                result,
                candidate_years=result.candidate_years,
                required_years=0,
                level_match=None,
                evidence=[],
            )

        return result.model_copy(
            update={
                "score": _score_or_zero(result.score),
                "status": "evaluated",
                "required_years": requirements.minimum_years,
            }
        )

    @staticmethod
    def _normalize_projects(
        result: ProjectsMatchingResult,
        requirements: EffectiveRequirements,
    ) -> ProjectsMatchingResult:
        if not requirements.projects_required and not requirements.project_domains:
            return _not_applicable(result, matches=[])

        matches = [
            ProjectMatch(
                project_name=item.project_name,
                matched_domain=(
                    item.matched_domain
                    if item.similarity_score >= MATCH_THRESHOLD
                    else None
                ),
                similarity_score=item.similarity_score,
                evidence=(
                    item.evidence
                    if item.similarity_score >= MATCH_THRESHOLD
                    else None
                ),
            )
            for item in result.matches
        ]
        return result.model_copy(
            update={
                "score": _score_or_zero(result.score),
                "status": "evaluated",
                "matches": matches,
            }
        )

    @staticmethod
    def _normalize_education(
        result: EducationMatchingResult,
        requirements: EffectiveRequirements,
    ) -> EducationMatchingResult:
        if not requirements.education:
            return _not_applicable(
                result,
                matched_field=None,
                evidence=None,
            )

        return result.model_copy(
            update={
                "score": _score_or_zero(result.score),
                "status": "evaluated",
            }
        )

    @staticmethod
    def _normalize_list_result(
        result: ListMatchingResult,
        requirements: tuple[str, ...],
    ) -> ListMatchingResult:
        if not requirements:
            return _not_applicable(result, matched=[], missing=[])

        matched_keys = {_key(item) for item in result.matched}
        matched = [item for item in requirements if _key(item) in matched_keys]
        missing = [item for item in requirements if _key(item) not in matched_keys]
        return result.model_copy(
            update={
                "score": _score_or_zero(result.score),
                "status": "evaluated",
                "matched": matched,
                "missing": missing,
            }
        )
