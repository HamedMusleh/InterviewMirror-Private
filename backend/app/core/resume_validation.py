"""Single source of truth for resume upload validation.

Shared by the standalone CV parser endpoint and the application
submission flow so both enforce the same rules.
"""

ALLOWED_RESUME_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024
