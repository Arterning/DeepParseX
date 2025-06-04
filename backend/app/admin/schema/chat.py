from backend.common.schema import SchemaBase


class ChatParam(SchemaBase):
    question:str
    doc_id:int | None = None

class IdParam(SchemaBase):
    id:int