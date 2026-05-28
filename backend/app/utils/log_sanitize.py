from typing import Any

_MAX_LOG_LEN = 200


def sanitize_log(value: Any, max_len: int = _MAX_LOG_LEN) -> str:
    """Strip CR/LF/TAB and other control chars from values flowing into log records.

    Use on any user-controlled value before interpolating into a log message — prevents
    log forging (CWE-117) where attacker-supplied newlines split or spoof log lines.
    """
    s = str(value)
    s = s.replace("\r", "").replace("\n", " ").replace("\t", " ")
    s = "".join(ch for ch in s if ch >= " " or ch == " ")
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
