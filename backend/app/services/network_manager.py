import os
import aiohttp
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self):
        self.gluetun_path = "/app/gluetun"
        self.wg_config_path = os.path.join(self.gluetun_path, "wireguard.conf")
        self.wg_env_path = os.path.join(self.gluetun_path, "wg_env")
        
        # Proxies accessible from backend container
        self.proxies = {
            "direct": None,
            "vpn": "http://audiovault-vpn:8888",
            "tor": "socks5://audiovault-vpn:9050", 
            "tor_vpn": "socks5://audiovault-vpn:9050" 
        }
        
        # Ensure env file exists on startup
        self.ensure_env_file()

    def ensure_env_file(self):
        """Create empty/default env file if missing"""
        try:
            os.makedirs(self.gluetun_path, exist_ok=True)
            if not os.path.exists(self.wg_env_path):
                # Default logic: Use dummy keys to prevent crash loop on fresh start
                # These keys are syntactically valid (Base64 32-byte) but functional
                dummy_env = (
                    "# Auto-generated Placeholder Config\n"
                    "WIREGUARD_PRIVATE_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
                    "WIREGUARD_PUBLIC_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
                    "WIREGUARD_ADDRESSES=10.0.0.1/32\n"
                    "VPN_ENDPOINT_IP=127.0.0.1\n"
                    "VPN_ENDPOINT_PORT=51820\n"
                )
                with open(self.wg_env_path, "w", encoding="utf-8") as f:
                    f.write(dummy_env)
                logger.info("Created placeholder vpn env file.")
        except Exception as e:
            logger.error(f"Failed to create env file: {e}")

    async def get_public_ip(self, mode: str = "direct") -> Dict[str, str]:
        """Check public IP using specified mode/proxy"""
        proxy_url = self.proxies.get(mode)
        url = "https://api.ipify.org?format=json"
        
        connector = None
        try:
            # Create appropriate connector for SOCKS/HTTP proxies
            if proxy_url:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy_url)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                timeout = aiohttp.ClientTimeout(total=20) 
                # Note: proxy parameter is NOT used when using a connector
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"ip": data.get("ip"), "status": "connected", "mode": mode}
                    else:
                        # Tor usually returns 501 if accessed incorrectly, but here we catch upstream errors
                        return {"error": f"HTTP {response.status}", "status": "error", "mode": mode}
        except ImportError:
             logger.error("aiohttp-socks not installed")
             return {"error": "Missing dependency", "status": "error", "mode": mode}
        except Exception as e:
            logger.error(f"IP check failed for mode {mode} with proxy {proxy_url}: {e}")
            # If using connector, it must be closed (handled by context manager usually but good to be safe)
            return {"error": str(e), "status": "unreachable", "mode": mode}

    def parse_config_value(self, content: str, key: str) -> Optional[str]:
        """Extract value from line 'Key = Value'"""
        for line in content.splitlines():
            line = line.split('#')[0].strip()
            if '=' in line:
                k, v = line.split('=', 1)
                if k.strip().lower() == key.lower():
                    return v.strip()
        return None

    def save_wireguard_config(self, config_content: str) -> bool:
        """Parse config and save as Environment Variables for Gluetun"""
        try:
            # Parse required fields
            private_key = self.parse_config_value(config_content, "PrivateKey")
            public_key = self.parse_config_value(config_content, "PublicKey")
            address = self.parse_config_value(config_content, "Address")
            endpoint = self.parse_config_value(config_content, "Endpoint")

            if not all([private_key, public_key, address, endpoint]):
                logger.error("Missing required WireGuard fields in config")
                return False

            # Parse Endpoint Host/IP and Port
            if ':' in endpoint:
                endpoint_ip, endpoint_port = endpoint.split(':', 1)
            else:
                endpoint_ip = endpoint
                endpoint_port = "51820"

            env_content = (
                f"VPN_ENDPOINT_IP={endpoint_ip}\n"
                f"VPN_ENDPOINT_PORT={endpoint_port}\n"
                f"WIREGUARD_PRIVATE_KEY={private_key}\n"
                f"WIREGUARD_PUBLIC_KEY={public_key}\n"
                f"WIREGUARD_ADDRESSES={address}\n"
            )

            os.makedirs(self.gluetun_path, exist_ok=True)
            
            # Save ENV file (robust method)
            with open(self.wg_env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            
            # ALSO save the conf file just as backup/reference (for UI load maybe?)
            with open(self.wg_config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            
            logger.info("WireGuard config converted to ENV and saved.")
            return True
        except Exception as e:
            logger.error(f"Failed to process WireGuard config: {e}")
            return False

    def get_proxy_url(self, mode: str) -> Optional[str]:
        return self.proxies.get(mode)

network_manager = NetworkManager()
