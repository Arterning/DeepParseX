from backend.common.schema import SchemaBase


class ChatParam(SchemaBase):
    question: str
    doc_id: int | None = None
    session_id: int | None = None
    doc_dir_ids: list[int] | None = None
    send_history: bool | None = None
    agent_mode: bool | None = None

class IdParam(SchemaBase):
    id:int

class TranslateParam(SchemaBase):
    id:int | None = None
    target_language : str | None = "中文"
    text: str | None = None

class ChatDocParam(SchemaBase):
    question: str
    context: str
    doc_id: int | None = None
