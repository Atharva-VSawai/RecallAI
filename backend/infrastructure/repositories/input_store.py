import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from core.config import settings

logger = logging.getLogger(__name__)

class InputStore(ABC):
    @abstractmethod
    def store(self, organization_id: str, project_id: str, job_id: str, content: bytes, filename: str, content_type: str) -> Tuple[str, str, int]:
        """Stores input and returns (uri, checksum, size)"""
        pass

    @abstractmethod
    def retrieve(self, uri: str) -> bytes:
        pass


class LocalInputStore(InputStore):
    """Fallback local disk store for development/testing."""
    def __init__(self, base_dir: str = "data/inputs"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def store(self, organization_id: str, project_id: str, job_id: str, content: bytes, filename: str, content_type: str) -> Tuple[str, str, int]:
        size = len(content)
        checksum = hashlib.sha256(content).hexdigest()
        
        org_dir = os.path.join(self.base_dir, organization_id, project_id)
        os.makedirs(org_dir, exist_ok=True)
        
        
        safe_filename = os.path.basename(filename)
        file_path = os.path.abspath(os.path.join(org_dir, f"{job_id}_{safe_filename}"))
        if not file_path.startswith(os.path.abspath(self.base_dir)):
            raise ValueError("Path traversal attempt detected")
            
        with open(file_path, "wb") as f:
            f.write(content)
            
        uri = f"local://{file_path}"
        return uri, checksum, size

    def retrieve(self, uri: str) -> bytes:
        if not uri.startswith("local://"):
            raise ValueError("Invalid local URI")
        file_path = os.path.abspath(uri.replace("local://", "", 1))
        if not file_path.startswith(os.path.abspath(self.base_dir)):
            raise ValueError("Path traversal attempt detected in URI")
        with open(file_path, "rb") as f:
            return f.read()

class SupabaseInputStore(InputStore):
    """Production object storage using Supabase Storage."""
    def __init__(self, bucket_name: str = "ingestion_inputs"):
        from db.supabase_client import supabase
        self.supabase = supabase
        self.bucket_name = bucket_name

    def store(self, organization_id: str, project_id: str, job_id: str, content: bytes, filename: str, content_type: str) -> Tuple[str, str, int]:
        size = len(content)
        checksum = hashlib.sha256(content).hexdigest()
        
        path = f"{organization_id}/{project_id}/{job_id}/{filename}"
        
        try:
            self.supabase.storage.from_(self.bucket_name).upload(
                file=content,
                path=path,
                file_options={"content-type": content_type, "upsert": "true"}
            )
        except Exception as e:
            logger.error(f"Failed to upload to Supabase storage: {e}")
            raise
            
        uri = f"supabase://{self.bucket_name}/{path}"
        return uri, checksum, size

    def retrieve(self, uri: str) -> bytes:
        if not uri.startswith("supabase://"):
            raise ValueError("Invalid supabase URI")
        
        parts = uri.replace("supabase://", "", 1).split("/", 1)
        bucket = parts[0]
        path = parts[1]
        
        response = self.supabase.storage.from_(bucket).download(path)
        return response

def get_input_store() -> InputStore:
    # Use local storage if no service role key is provided, as anon key shouldn't be used for backend storage writes
    if settings.supabase_service_role_key and settings.supabase_service_role_key != "your-supabase-service-role-key-here":
        return SupabaseInputStore()
    else:
        logger.warning("Using LocalInputStore. Not suitable for production.")
        return LocalInputStore()
