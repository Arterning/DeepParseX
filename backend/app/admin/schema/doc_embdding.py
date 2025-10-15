
from backend.common.schema import SchemaBase


class SysDocEmbeddingSchemaBase(SchemaBase):
    doc_id: int
    doc_name: str
    chunk_text: str
    embedding: list[float]
    embedding_384: list[float]
    embedding_768: list[float]
    embedding_1536: list[float]
    embedding_3072: list[float]

class CreateSysDocEmbeddingParam(SysDocEmbeddingSchemaBase):
    pass