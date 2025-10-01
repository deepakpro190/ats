from pydantic import BaseModel

class UploadRequest(BaseModel):
    keywords: str = ""
