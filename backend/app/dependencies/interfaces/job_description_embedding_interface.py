from abc import ABC, abstractmethod
from typing import Dict, List
from app.schemas.job_description import JobDescriptionResponse

class JobDescriptionEmbeddingInterface(ABC):

    @abstractmethod
    def generate_job_description_embeddings(
        self,
        job: JobDescriptionResponse,
    ) -> Dict[str, List[float]]:
        pass