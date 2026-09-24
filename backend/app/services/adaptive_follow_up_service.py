from openai import AzureOpenAI

from app.prompts.adaptive_follow_up_prompt import (
    ADAPTIVE_FOLLOW_UP_SYSTEM_PROMPT,
)
from app.schemas.adaptive_follow_up import (
    FollowUpQuestionRequest,
    FollowUpQuestionResponse,
    GeneratedFollowUp,
)
from app.services.llm_client import AZURE_OPENAI_DEPLOYMENT_NAME


class AdaptiveFollowUpService:
    def __init__(self, client: AzureOpenAI):
        self.client = client

    def generate_follow_up_question(
        self,
        request: FollowUpQuestionRequest,
    ) -> FollowUpQuestionResponse | None:
        if not request.follow_up_needed:
            return None

        missing_areas = ", ".join(request.missing_areas) or "None"

        response = self.client.chat.completions.parse(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": ADAPTIVE_FOLLOW_UP_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Current question: {request.question}\n"
                        f"Candidate answer: {request.answer}\n"
                        f"Follow-up reason: {request.follow_up_reason}\n"
                        f"Missing areas: {missing_areas}\n"
                        f"Skill: {request.skill or 'None'}"
                    ),
                },
            ],
            response_format=GeneratedFollowUp,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Failed to generate a follow-up question.")

        return FollowUpQuestionResponse(
            parent_question_id=request.question_id,
            question=parsed.question,
            category=request.question_type,
            skill=request.skill,
        )