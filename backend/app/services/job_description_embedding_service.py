from typing import Dict, List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.schemas.job_description import JobDescriptionResponse
from app.dependencies.interfaces.job_description_embedding_interface import (
    JobDescriptionEmbeddingInterface,
)

class JobDescriptionEmbeddingService(
    JobDescriptionEmbeddingInterface
):

    """
    Generate semantic embeddings for relevant job description sections.
    Hard requirements remain structured for filtering and scoring.
    """

    def __init__(self):
        self.model = SentenceTransformer("all-mpnet-base-v2")

    def build_semantic_sections(
        self,
        job: JobDescriptionResponse,
    ) -> Dict[str, str]:
        """
        Build meaningful semantic sections for embedding generation.
        """
        sections: Dict[str, str] = {}

        role_parts = [
            job.role.title.strip(),
            job.role.department.strip(),
        ]
        sections["role"] = " ".join(
            value for value in role_parts if value
        )

        if job.job_summary.strip():
            sections["job_summary"] = job.job_summary.strip()

        if job.responsibilities:
            sections["responsibilities"] = ". ".join(
                job.responsibilities
            )

        if job.requirements.skills.preferred:
            sections["preferred_skills"] = ", ".join(
                job.requirements.skills.preferred
            )

        if job.soft_skills:
            sections["soft_skills"] = ", ".join(
                job.soft_skills
            )

        return {
            name: text
            for name, text in sections.items()
            if text.strip()
        }

    def build_hard_requirements(
        self,
        job: JobDescriptionResponse,
    ) -> dict:
        """
        Keep explicit requirements separate from semantic embeddings.
        """
        return {
            "required_skills": job.requirements.skills.required,
            "minimum_years": (
                job.requirements.experience.minimum_years
            ),
            "experience_level": (
                job.requirements.experience.level
            ),
            "education": job.requirements.education,
            "certifications": job.requirements.certifications,
            "languages": job.requirements.languages,
            "technical_stack": job.technical_stack,
        }

    def _chunk_text(
        self,
        text: str,
    ) -> List[str]:
        """
        Split long text into chunks that fit within the model token limit.
        """
        max_tokens = self.model.max_seq_length - 2

        tokens = self.model.tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        chunks = []

        for start in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[start:start + max_tokens]

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
        Generate one normalized embedding while safely handling long text.
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

        norm = np.linalg.norm(combined_embedding)

        if norm > 0:
            combined_embedding = combined_embedding / norm

        return combined_embedding.tolist()

    def generate_job_description_embeddings(
        self,
        job: JobDescriptionResponse,
    ) -> Dict[str, List[float]]:
        """
        Generate separate embeddings for meaningful semantic sections.
        """
        sections = self.build_semantic_sections(job)

        return {
            name: self.generate_embedding(text)
            for name, text in sections.items()
        }