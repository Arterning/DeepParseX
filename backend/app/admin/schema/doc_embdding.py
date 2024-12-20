
from backend.common.schema import SchemaBase


class SysDocEmbeddingSchemaBase(SchemaBase):
    doc_id: int
    doc_name: str
    desc: str
    embedding: list[float]

class CreateSysDocEmbeddingParam(SysDocEmbeddingSchemaBase):
    pass