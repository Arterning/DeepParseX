
from backend.common.schema import SchemaBase


class SysDocEmbeddingSchemaBase(SchemaBase):
    doc_id: int
    doc_name: str
    chunk_text: str
    embedding: list[float] | None = None
    embedding_384: list[float] | None = None
    embedding_768: list[float] | None = None
    embedding_1536: list[float] | None = None
    embedding_3072: list[float] | None = None

class CreateSysDocEmbeddingParam(SysDocEmbeddingSchemaBase):
    pass