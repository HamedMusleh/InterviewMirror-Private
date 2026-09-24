from azure.ai.documentintelligence import (
    DocumentIntelligenceClient,
)
from azure.core.credentials import AzureKeyCredential

from app.core.config import (
    AZURE_DOC_INTEL_ENDPOINT,
    AZURE_DOC_INTEL_KEY,
)


class DocumentIntelligenceService:

    def __init__(self):

        if (
            not AZURE_DOC_INTEL_ENDPOINT
            or not AZURE_DOC_INTEL_KEY
        ):
            raise ValueError(
                "Missing Azure Document Intelligence credentials"
            )

        self.client = DocumentIntelligenceClient(
            endpoint=AZURE_DOC_INTEL_ENDPOINT,
            credential=AzureKeyCredential(
                AZURE_DOC_INTEL_KEY
            ),
        )

    def extract_text(
        self,
        file_content: bytes,
    ):

        poller = self.client.begin_analyze_document(
            "prebuilt-read",
            body=file_content,
        )

        result = poller.result()

        text = ""

        for page in result.pages:
            for line in page.lines:
                text += line.content + "\n"

        return text