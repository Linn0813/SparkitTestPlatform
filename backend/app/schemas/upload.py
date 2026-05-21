from pydantic import BaseModel

from app.schemas.common import ORMBase


class ProjectUploadOut(BaseModel):
    object_key: str
    filename: str
    size: int
    content_type: str
    kind: str
    url: str


class FileUrlOut(BaseModel):
    url: str
