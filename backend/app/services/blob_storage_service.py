from datetime import datetime, timedelta, timezone
from uuid import uuid4

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
)

from app.core.config import (
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_STORAGE_CONTAINER_NAME,
)


class BlobStorageService:

    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        self.container_client = (
            self.blob_service_client.get_container_client(
                AZURE_STORAGE_CONTAINER_NAME
            )
        )

    def upload_audio(
        self,
        audio_data: bytes,
        blob_name: str,
        content_type: str,
    ) -> str:

        if not audio_data:
            raise ValueError("Audio data is empty.")

        blob_client = self.container_client.get_blob_client(blob_name)

        blob_client.upload_blob(
            audio_data,
            overwrite=True,
            content_settings=ContentSettings(
                content_type=content_type,
            ),
        )

        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            container_name=AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        return f"{blob_client.url}?{sas_token}"