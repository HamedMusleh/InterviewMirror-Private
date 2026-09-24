from functools import lru_cache

from app.services.blob_storage_service import BlobStorageService


@lru_cache
def get_blob_storage_service() -> BlobStorageService:
    return BlobStorageService()