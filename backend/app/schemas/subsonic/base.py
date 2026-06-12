"""
Base schemas and response helpers for Subsonic API.

Subsonic API uses a specific response format with nested 'subsonic-response' object.
"""

import re
import xml.etree.ElementTree as ET  # nosec B405
from typing import Any

from fastapi import Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Pattern to match illegal XML 1.0 characters (control chars except tab, newline, carriage return)
# XML 1.0 allows: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
_ILLEGAL_XML_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def xml_safe_string(value: str) -> str:
    """
    Remove illegal XML 1.0 control characters from string.

    XML 1.0 does not allow certain control characters (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F).
    If these are present in song titles or other metadata, the XML will be malformed
    and clients like Amperfy will fail to parse it, causing songs to be skipped.

    Args:
        value: String that may contain illegal characters

    Returns:
        Sanitized string safe for XML serialization
    """
    return _ILLEGAL_XML_CHARS_RE.sub("", value)


class SubsonicError(BaseModel):
    """Subsonic error object."""

    code: int
    message: str


class SubsonicResponseWrapper(BaseModel):
    """
    Wrapper for Subsonic API responses.

    All Subsonic responses are wrapped in a 'subsonic-response' object.
    """

    status: str = "ok"
    version: str = "1.16.1"
    serverVersion: str = "1.0.0"  # noqa: N815
    type: str = "audiovault"
    openSubsonic: bool = True  # noqa: N815

    error: SubsonicError | None = None

    class Config:
        extra = "allow"


# Subsonic error codes
SUBSONIC_ERROR_CODES = {
    0: "A generic error",
    10: "Required parameter is missing",
    20: "Incompatible Subsonic REST protocol version",
    30: "Incompatible Subsonic REST protocol version (server)",
    40: "Wrong username or password",
    41: "Token authentication not supported for LDAP users",
    50: "User is not authorized for the given operation",
    60: "Trial period is over",
    70: "The requested data was not found",
}


def _set_xml_attr(parent: ET.Element, key: str, value: Any) -> None:
    if isinstance(value, bool):
        parent.set(key, "true" if value else "false")
    elif isinstance(value, str):
        parent.set(key, xml_safe_string(value))
    else:
        parent.set(key, str(value))


def _build_xml_element(parent: ET.Element, data: Any) -> None:
    if isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _build_xml_element(child, item)
        return
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        if isinstance(value, dict):
            child = ET.SubElement(parent, key)
            _build_xml_element(child, value)
        elif isinstance(value, list):
            for item in value:
                child = ET.SubElement(parent, key)
                _build_xml_element(child, item)
        elif value is not None:
            _set_xml_attr(parent, key, value)


def dict_to_xml(tag: str, d: Any) -> str:
    """Simple dict to XML converter for Subsonic format."""
    elem = ET.Element(tag)
    _build_xml_element(elem, d)
    elem.set("xmlns", "http://subsonic.org/restapi")
    return ET.tostring(elem, encoding="unicode", method="xml")


def strip_none(value: Any) -> Any:
    """
    Recursively drop keys whose value is None from dicts (lists handled too).

    The Subsonic JSON profile must omit optional fields rather than emit them as
    ``null``. Strict clients (notably Symfonium, which uses a Moshi/Kotlin parser
    with non-nullable field types) abort parsing the whole response on an
    unexpected ``null`` and report a sync failure, while lenient clients
    (Amperfy, substreamer) tolerate it. The XML branch already skips None in
    ``_build_xml_element``; this keeps the JSON branch consistent.
    """
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(item) for item in value]
    return value


def subsonic_response(data: dict[str, Any] | None = None, f: str = "json") -> Any:
    """
    Build a successful Subsonic response.

    Args:
        data: Optional data to include in the response
        f: Format ('json' or 'xml')

    Returns:
        Dict with Subsonic response format or Response object with XML
    """
    response = {
        "status": "ok",
        "version": "1.16.1",
        "serverVersion": "1.0.0",
        "type": "audiovault",
        "openSubsonic": True,
    }

    if data:
        response.update(data)

    if f == "json":
        return {"subsonic-response": strip_none(response)}
    else:
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + dict_to_xml("subsonic-response", response)
        return Response(content=xml_str, media_type="application/xml")


def subsonic_error_response(code: int, message: str | None = None, f: str = "json") -> Response:
    """
    Build a Subsonic error as a concrete Response object (always HTTP 200).

    Unlike subsonic_error (which returns a plain dict for JSON so FastAPI can
    serialize it from a handler return), this always returns a Response. It is
    meant for exception handlers, where the Subsonic spec requires HTTP 200 with
    the error envelope in the body rather than a transport-level 4xx status.
    """
    result = subsonic_error(code, message, f)
    if isinstance(result, Response):
        # XML branch already returns a 200 Response
        return result
    return JSONResponse(status_code=200, content=result)


def subsonic_error(code: int, message: str | None = None, f: str = "json") -> Any:
    """
    Build a Subsonic error response.

    Args:
        code: Subsonic error code
        message: Optional custom error message
        f: Format ('json' or 'xml')

    Returns:
        Dict with Subsonic error response format or Response object with XML
    """
    if message is None:
        message = SUBSONIC_ERROR_CODES.get(code, "Unknown error")

    response = {
        "status": "failed",
        "version": "1.16.1",
        "serverVersion": "1.0.0",
        "type": "audiovault",
        "openSubsonic": True,
        "error": {
            "code": code,
            "message": message,
        },
    }

    if f == "json":
        return {"subsonic-response": response}
    else:
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + dict_to_xml("subsonic-response", response)
        return Response(content=xml_str, media_type="application/xml")
