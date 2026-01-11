import logging

import aiohttp

logger = logging.getLogger(__name__)


async def resolve_redirects(url: str) -> str:
    """
    Follows redirects to get the final URL.
    Useful for short links like spotify.link, amzn.to, youtu.be, etc.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Head request first to be faster/lighter
            async with session.head(url, allow_redirects=True) as response:
                return str(response.url)
    except Exception as e:
        logger.warning(f"Failed to resolve URL {url}: {e}")
        # If head fails (e.g. 405 Method Not Allowed), try GET stream=True
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True) as response:
                    return str(response.url)
        except Exception as e2:
            logger.error(f"Failed to resolve URL {url} with GET: {e2}")
            return url
