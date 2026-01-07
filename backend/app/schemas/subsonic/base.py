"""
Base schemas and response helpers for Subsonic API.

Subsonic API uses a specific response format with nested 'subsonic-response' object.
"""

from typing import Any

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


def subsonic_response(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a successful Subsonic response.
    
    Args:
        data: Optional data to include in the response
        
    Returns:
        Dict with Subsonic response format
        
    Example:
        >>> subsonic_response({"song": {"id": "123", "title": "Test"}})
        {
            "subsonic-response": {
                "status": "ok",
                "version": "1.16.1",
                "song": {"id": "123", "title": "Test"}
            }
        }
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
    
    return {"subsonic-response": response}


def subsonic_error(code: int, message: str | None = None) -> dict[str, Any]:
    """
    Build a Subsonic error response.
    
    Args:
        code: Subsonic error code (0, 10, 20, 30, 40, 50, 60, 70)
        message: Optional custom error message
        
    Returns:
        Dict with Subsonic error response format
        
    Example:
        >>> subsonic_error(40, "Invalid credentials")
        {
            "subsonic-response": {
                "status": "failed",
                "version": "1.16.1",
                "error": {"code": 40, "message": "Invalid credentials"}
            }
        }
    """
    if message is None:
        message = SUBSONIC_ERROR_CODES.get(code, "Unknown error")
    
    return {
        "subsonic-response": {
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
    }
