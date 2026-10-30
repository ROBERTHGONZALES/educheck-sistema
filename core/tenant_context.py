from contextvars import ContextVar

current_school_id: ContextVar[int | None] = ContextVar("current_school_id", default=None)
