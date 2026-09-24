from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.schemas.resume import ResumeSchema


class EmbeddingService:
    """
    Generate semantic embeddings for meaningful resume sections.
    Hard requirements remain structured for filtering and scoring.
    """

    def __init__(self):
        self.model = SentenceTransformer(
            "all-mpnet-base-v2"
        )

    def build_semantic_sections(
        self,
        resume: ResumeSchema,
    ) -> Dict[str, str]:
        """
        Build meaningful semantic sections for embedding generation.
        """

        sections: Dict[str, str] = {}

        if resume.professional_summary:
            sections["professional_summary"] = (
                resume.professional_summary.strip()
            )

        skills = []

        skills.extend(resume.skills.technical)
        skills.extend(resume.skills.tools_and_technologies)
        skills.extend(resume.skills.soft)

        if skills:
            sections["skills"] = ", ".join(skills)

        experience_sections = []

        for exp in resume.experience:
            experience_text = []

            if exp.job_title:
                experience_text.append(
                    f"Role: {exp.job_title}"
                )

            if exp.company:
                experience_text.append(
                    f"Company: {exp.company}"
                )

            if exp.duration:
                experience_text.append(
                    f"Duration: {exp.duration}"
                )

            if exp.years:
                experience_text.append(
                    f"Years: {exp.years}"
                )

            if exp.responsibilities:
                experience_text.append(
                    "Responsibilities: "
                    + ", ".join(exp.responsibilities)
                )

            if exp.technical_stack:
                experience_text.append(
                    "Technologies: "
                    + ", ".join(exp.technical_stack)
                )

            if experience_text:
                experience_sections.append(
                    "\n".join(experience_text)
                )

        if experience_sections:
            sections["experience"] = "\n\n".join(
                experience_sections
            )

        project_sections = []

        for project in resume.projects:
            project_text = []

            if project.name:
                project_text.append(
                    f"Project: {project.name}"
                )

            if project.description:
                project_text.append(
                    f"Description: {project.description}"
                )

            if project.technical_stack:
                project_text.append(
                    "Technologies: "
                    + ", ".join(project.technical_stack)
                )

            if project_text:
                project_sections.append(
                    "\n".join(project_text)
                )

        if project_sections:
            sections["projects"] = "\n\n".join(
                project_sections
            )

        return {
            name: text
            for name, text in sections.items()
            if text.strip()
        }

    def build_hard_requirements(
        self,
        resume: ResumeSchema,
    ) -> dict:
        """
        Keep explicit resume requirements separate
        from semantic embeddings.
        """

        return {
            "location": resume.personal_information.location,
            "experience": resume.experience,
            "education": resume.education,
            "certifications": resume.certifications,
            "languages": resume.languages,
        }

    def _chunk_text(
        self,
        text: str,
    ) -> List[str]:
        """
        Split long text into chunks that fit within
        the model token limit.
        """

        max_tokens = self.model.max_seq_length - 2

        tokens = self.model.tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        chunks = []

        for start in range(
            0,
            len(tokens),
            max_tokens,
        ):
            chunk_tokens = tokens[
                start:start + max_tokens
            ]

            chunk = self.model.tokenizer.decode(
                chunk_tokens,
                skip_special_tokens=True,
            ).strip()

            if chunk:
                chunks.append(chunk)

        return chunks

    def generate_embedding(
        self,
        text: str,
    ) -> List[float]:
        """
        Generate one normalized embedding while safely
        handling long text.
        """

        chunks = self._chunk_text(text)

        if not chunks:
            return []

        embeddings = self.model.encode(
            chunks,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        combined_embedding = np.mean(
            embeddings,
            axis=0,
        )

        norm = np.linalg.norm(
            combined_embedding
        )

        if norm > 0:
            combined_embedding = (
                combined_embedding / norm
            )

        return combined_embedding.tolist()

    def generate_resume_embeddings(
        self,
        resume: ResumeSchema,
    ) -> Dict[str, List[float]]:
        """
        Generate separate embeddings for each meaningful
        semantic resume section.
        """

        sections = self.build_semantic_sections(
            resume
        )

        return {
            name: self.generate_embedding(text)
            for name, text in sections.items()
        }