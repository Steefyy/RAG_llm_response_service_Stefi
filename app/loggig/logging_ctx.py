from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_var: ContextVar[str] = ContextVar("user", default="anonymous")
