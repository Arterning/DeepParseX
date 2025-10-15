
from backend.common.schema import SchemaBase


class SysDocChunkSchemaBase(SchemaBase):
    doc_id: int
    doc_name: str
    chunk_text: str

class CreateSysDocChunkParam(SysDocChunkSchemaBase):
    pass