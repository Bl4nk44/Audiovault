import os
import aiohttp
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self):
        self.gluetun_path = "/app/gluetun"
        self.wg_config_path = os.path.join(self.gluetun_path, "wireguard.conf")
        # Proxies accessible from backend container
        self.proxies = {
            "direct": None,
            "vpn": "http://audiovault-vpn:8888",
            "tor": "socks5://audiovault-vpn:9050", 
            # Tor over VPN is the same as Tor, because Tor container is behind VPN container physically
            "tor_vpn": "socks5://audiovault-vpn:9050" 
        }

    async def get_public_ip(self, mode: str = "direct") -> Dict[str, str]:
        """Check public IP using specified mode/proxy"""
        proxy = self.proxies.get(mode)
        url = "https://api.ipify.org?format=json"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Set timeout specifically for Tor which can be slow
                timeout = aiohttp.ClientTimeout(total=20) 
                async with session.get(url, proxy=proxy, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"ip": data.get("ip"), "status": "connected", "mode": mode}
                    else:
                        return {"error": f"HTTP {response.status}", "status": "error", "mode": mode}
        except Exception as e:
            logger.error(f"IP check failed for mode {mode}: {e}")
            return {"error": str(e), "status": "unreachable", "mode": mode}

    def save_wireguard_config(self, config_content: str) -> bool:
        """Save WireGuard configuration to the shared volume"""
        try:
            # Ensure directory exists
            os.makedirs(self.gluetun_path, exist_ok=True)
            
            with open(self.wg_config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            
            logger.info("WireGuard config saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save WireGuard config: {e}")
            return False

    def get_proxy_url(self, mode: str) -> Optional[str]:
        return self.proxies.get(mode)

network_manager = NetworkManager()
