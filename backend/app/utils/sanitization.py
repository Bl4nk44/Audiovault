import re


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """
    Sanitize filename to be safe on Windows, Linux and macOS.
    Removes or replaces characters that are illegal on these file systems.

    Windows forbidden: < > : " / \ | ? * and control chars.
    Linux/macOS forbidden: / and null char.

    This function applies the strictest rules (Windows) to ensure cross-platform safety.
    """
    if not name:
        return "unnamed"

    # 1. Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)

    # 2. Replace illegal characters for strict Windows compatibility
    # Pattern includes: < > : " / \ | ? *
    illegal_chars = r'[<>:"/\\|?*]'
    name = re.sub(illegal_chars, replacement, name)

    # 3. Strip leading/trailing spaces and dots (Windows issue)
    name = name.strip().strip(".")

    # 4. Enforce max length (255 chars is safe limit for most FS)
    if len(name) > 255:
        name = name[:255]

    return name if name else "unnamed"
