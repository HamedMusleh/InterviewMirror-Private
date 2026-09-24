from app.schemas.screening_score import (
    CategoryBreakdown,
    ScreeningScoreRequest,
    ScreeningScoreResponse,
)

MATCH_THRESHOLD = 50


def calculate_screening_score(
    request: ScreeningScoreRequest,
) -> ScreeningScoreResponse:
    category_breakdown = {}

    active_weight = 0.0
    weighted_score_total = 0.0

    matched_criteria = []
    missing_criteria = []

    for category_name, category in request.category_scores.items():
        if category.status == "not_applicable":
            category_breakdown[category_name] = CategoryBreakdown(
                score=None,
                weight=None,
                weighted_score=None,
                status="not_applicable",
            )
            continue

        weight = request.category_weights[category_name]

        weighted_score = category.score * weight / 100

        category_breakdown[category_name] = CategoryBreakdown(
            score=category.score,
            weight=weight,
            weighted_score=round(weighted_score, 2),
            status="evaluated",
        )

        weighted_score_total += weighted_score
        active_weight += weight

        if category.score is not None and category.score >= MATCH_THRESHOLD:
            matched_criteria.append(category_name)
        else:
            missing_criteria.append(category_name)

    if active_weight == 0:
        overall_score = 0.0
    else:
        overall_score = round(
            weighted_score_total / (active_weight / 100),
            2,
        )

    final_status = (
        "recommended"
        if overall_score >= request.passing_score
        else "not_recommended"
    )

    return ScreeningScoreResponse(
        candidate_id=request.candidate_id,
        job_id=request.job_id,
        application_id=request.application_id,
        criteria_id=request.criteria_id,
        category_breakdown=category_breakdown,
        matched_criteria=matched_criteria,
        missing_criteria=missing_criteria,
        matching_details=request.matching_details,
        overall_score=overall_score,
        passing_score=request.passing_score,
        final_status=final_status,
    )