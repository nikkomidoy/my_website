import logging

SENSITIVE_KEYS = frozenset(
    {"authorization", "cookie", "password", "body", "token", "access_token", "secret"}
)


class DropSensitiveKeysFilter(logging.Filter):
    """Strip sensitive keys from structlog event dicts / record attributes (GDPR)."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.msg
        if isinstance(msg, dict):
            for key in list(msg):
                if key.lower() in SENSITIVE_KEYS:
                    msg[key] = "[redacted]"
        for key in list(vars(record)):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, "[redacted]")
        return True
