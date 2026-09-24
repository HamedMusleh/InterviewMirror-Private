import os
import json
from uuid import uuid4

from dotenv import load_dotenv
from openai import AzureOpenAI

from app.schemas.resume import ResumeSchema

load_dotenv()


SYSTEM_PROMPT = """
You are an expert AI Resume Parser.

Extract the CV information and return ONLY valid JSON.

The JSON MUST follow exactly this structure:

{
  "candidate_id": "",
  "personal_information": {
    "name": "",
    "email": "",
    "location": ""
  },

  "professional_summary": "",

  "skills": {
    "technical": [],
    "tools_and_technologies": [],
    "soft": []
  },

  "experience": [
    {
      "job_title": "",
      "company": "",
      "duration": "",
      "years": 0,
      "responsibilities": [],
      "technical_stack": []
    }
  ],

  "education": [
    {
      "degree": "",
      "field": "",
      "institution": "",
      "graduation_year": 0
    }
  ],

  "projects": [
    {
      "name": "",
      "description": "",
      "technical_stack": []
    }
  ],

  "certifications": [],

  "languages": []
}


Rules:
- Do not add extra fields.
- Do not remove fields.
- Do not invent information.
- If information is missing, use empty string, empty array, or 0.
"""


class LLMExtractorService:


    def __init__(self):

        self.client = AzureOpenAI(

            azure_endpoint=os.getenv(
                "AZURE_OPENAI_ENDPOINT"
            ),

            api_key=os.getenv(
                "AZURE_OPENAI_KEY"
            ),

            api_version=os.getenv(
                "AZURE_OPENAI_API_VERSION"
            )
        )


        self.deployment = os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        )


    def extract_resume(self, text: str):

        response = self.client.chat.completions.create(

            model=self.deployment,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },

                {
                    "role": "user",
                    "content": text
                }
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0.1
        )


        result = response.choices[0].message.content


        data = json.loads(result)


        # Generate candidate ID automatically
        data["candidate_id"] = str(uuid4())


        return ResumeSchema.model_validate(data)