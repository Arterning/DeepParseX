
from backend.common.schema import SchemaBase


class SysDocChunkSchemaBase(SchemaBase):
    doc_id: int
    doc_name: str
    chunk_text: str
    chunk_embedding: list[float]

class CreateSysDocChunkParam(SysDocChunkSchemaBase):
    pass