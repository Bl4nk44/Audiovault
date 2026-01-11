"""
Base schemas and response helpers for Subsonic API.

Subsonic API uses a specific response format with nested 'subsonic-response' object.
"""

from typing import Any
import xml.etree.ElementTree as ET
from fastapi import Response
from pydantic import BaseModel


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
    serverVersion: str = "1.0.0"
    type: str = "audiovault"
    openSubsonic: bool = True
    
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


def dict_to_xml(tag: str, d: Any) -> str:
    """
    Simple dict to XML converter for Subsonic format.
    
    Audiovault Subsonic XML style:
    - Lists are children elements
    - Dicts are attributes if they contain simple values, or nested elements if complex
    """
    elem = ET.Element(tag)
    
    def build_xml(parent, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    # Nested dict -> create single child element
                    child = ET.SubElement(parent, key)
                    build_xml(child, value)
                elif isinstance(value, list):
                    # List -> create sibling children with the same name (flattened)
                    # The key of the dict becomes the tag name for EACH item
                    child_tag = key
                    
                    # Special overrides if needed, but usually exact key match works
                    # for standard Subsonic JSON (e.g., 'song', 'album', 'child')
                    
                    for item in value:
                        child = ET.SubElement(parent, child_tag)
                        build_xml(child, item)
                elif value is not None:
                    # Attribute
                    val_str = str(value)
                    if isinstance(value, bool):
                        val_str = "true" if value else "false"
                    parent.set(key, val_str)
        
        elif isinstance(data, list):
            # Should not happen given the structure above, but just in case
            # If we passed a list to the root or something
            for item in data:
                child = ET.SubElement(parent, "item")
                build_xml(child, item)
                
    build_xml(elem, d)
    # Add namespace for subsonic
    elem.set("xmlns", "http://subsonic.org/restapi")
    
    return ET.tostring(elem, encoding='unicode', method='xml')


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
        return {"subsonic-response": response}
    else:
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + dict_to_xml("subsonic-response", response)
        return Response(content=xml_str, media_type="application/xml")


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
        }
    }
    
    if f == "json":
        return {"subsonic-response": response}
    else:
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + dict_to_xml("subsonic-response", response)
        return Response(content=xml_str, media_type="application/xml")
