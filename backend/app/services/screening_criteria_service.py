import json

from openai import AzureOpenAI

from app.core.logging import ILogger

from .llm_client import AZURE_OPENAI_DEPLOYMENT_NAME
from app.prompts.screening_prompt import (
    SCREENING_CRITERIA_SYSTEM_PROMPT,
    build_user_prompt,
)
from app.schemas.job_description import JobDescription, JobDescriptionResponse
from app.schemas.screening_criteria import ScreeningCriteria

DEFAULT_PASSING_SCORE = 70


def _build_strict_json_schema(model) -> dict:
    """
    Builds a JSON schema from a Pydantic model that is compatible with
    Azure OpenAI's Structured Outputs `strict: True` mode.

    Azure's strict mode requires every object in the schema to list
    ALL of its properties under "required" (even ones that have a
    default value in Pydantic - Pydantic only lists fields without a
    default there). This function does not change the Pydantic models
    themselves (fields, types, and defaults stay exactly as defined);
    it only patches the *generated JSON schema* dict, recursively,
    across every object definition (including nested ones under
    "$defs"), so Azure accepts it.
    """
    schema = model.model_json_schema()

    def _patch(node: dict) -> None:
        if not isinstance(node, dict):
            return

        if node.get("type") == "object" and "properties" in node:
            node["required"] = list(node["properties"].keys())
            for prop_schema in node["properties"].values():
                _patch(prop_schema)

        if "items" in node:
            _patch(node["items"])

        for key in ("$defs", "definitions"):
            if key in node:
                for def_schema in node[key].values():
                    _patch(def_schema)

    _patch(schema)
    return schema


def _normalize_skill_weights(parsed: dict, logger: ILogger) -> dict:
    """
    Ensures the sum of individual skill weights (required + preferred)
    exactly matches the total skills.weight, by rescaling them
    proportionally. If no skills are provided, the result is valid
    without normalization.
    """
    skills = parsed.get("screening_criteria", {}).get("skills", {})
    total_weight = skills.get("weight", 0)

    required = skills.get("required", [])
    preferred = skills.get("preferred", [])
    all_skills = required + preferred

    # No skills required: valid by default, no normalization needed.
    if not all_skills:
        return parsed

    current_sum = sum(s.get("weight", 0) for s in all_skills)

    # Skills are required, but all generated skill weights are zero.
    if current_sum == 0:
        raise ValueError(
            "Cannot normalize skill weights because all generated "
            "skill weights are zero."
        )

    # Skills have valid weights, but their sum does not match the total.
    if current_sum != total_weight:
        logger.warning(
            f"Skill weights sum ({current_sum}) did not match total skills "
            f"weight ({total_weight}). Rescaling proportionally."
        )

        scale = total_weight / current_sum

        for s in all_skills:
            s["weight"] = round(s["weight"] * scale, 2)

        rounded_sum = sum(s.get("weight", 0) for s in all_skills)
        remainder = round(total_weight - rounded_sum, 2)

        if remainder != 0:
            all_skills[-1]["weight"] = round(
                all_skills[-1]["weight"] + remainder, 2
            )

    return parsed


def generate_screening_criteria(
    job_description: JobDescriptionResponse,
    logger: ILogger,
    client: AzureOpenAI,
) -> ScreeningCriteria:
    """
    Generate a Screening Criteria JSON from a structured Job Description
    using a model deployed on Microsoft Foundry, and validate the output
    against the expected schema.

    Args:
        job_description: Validated JobDescription object.
        logger: ILogger instance injected by the caller (the pipeline).
        client: AzureOpenAI client injected by the caller.

    Returns:
        ScreeningCriteria: Validated screening criteria object.
    """
    passing_score = (
        job_description.screening_settings.passing_score
        if job_description.screening_settings
        else DEFAULT_PASSING_SCORE
    )

    job_description_json = job_description.model_dump_json(indent=2)
    user_prompt = build_user_prompt(
        job_description_json,
        passing_score=passing_score,
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SCREENING_CRITERIA_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "screening_criteria",
                    "strict": True,
                    "schema": _build_strict_json_schema(ScreeningCriteria),
                },
            },
            temperature=0.3,
        )

        raw_output = response.choices[0].message.content
        parsed = json.loads(raw_output)

        # Ensure job_id is always carried over from the input,
        # regardless of the model's output
        parsed["job_id"] = job_description.job_id

        # Guarantee the individual skill weights always sum to
        # the total skills weight, regardless of whether the model
        # followed the rule precisely
        parsed = _normalize_skill_weights(parsed, logger)

        return ScreeningCriteria(**parsed)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM output as JSON: {e}")
        raise

    except Exception as e:
        logger.error(f"Error generating screening criteria: {e}")
        raise


