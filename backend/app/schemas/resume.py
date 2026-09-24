from pydantic import BaseModel
from typing import List
from typing import Optional

class PersonalInformation(BaseModel):
    name: str = ""
    email: str = ""
    location: str = ""


class Skills(BaseModel):
    technical: List[str] = []
    tools_and_technologies: List[str] = []
    soft: List[str] = []


class Experience(BaseModel):
    job_title: str = ""
    company: str = ""
    duration: str = ""
    years: float = 0

    responsibilities: List[str] = []
    technical_stack: List[str] = []


class Education(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    graduation_year: int = 0


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technical_stack: List[str] = []


class ResumeSchema(BaseModel):

    candidate_id: Optional[str] = None

    personal_information: PersonalInformation = PersonalInformation()

    professional_summary: str = ""

    skills: Skills = Skills()

    experience: List[Experience] = []

    education: List[Education] = []

    projects: List[Project] = []

    certifications: List[str] = []

    languages: List[str] = []