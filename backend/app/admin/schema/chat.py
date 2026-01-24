from backend.common.schema import SchemaBase


class ChatParam(SchemaBase):
    question:str
    doc_id:int | None = None
    session_id:int | None = None

class IdParam(SchemaBase):
    id:int

class TranslateParam(SchemaBase):
    id:int | None = None
    target_language : str | None = "中文"
    text: str | None = None