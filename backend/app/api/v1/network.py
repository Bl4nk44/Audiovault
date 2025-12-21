from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.network_manager import network_manager
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

class NetworkConfig(BaseModel):
    wireguard_config: str

class NetworkModeUpdate(BaseModel):
    mode: str # direct, vpn, tor, tor_vpn

@router.get("/status")
async def get_network_status(current_user: User = Depends(get_current_active_user)):
    """Check connectivity across different modes"""
    # Parallelize checks? For now sequential is safer to not overload
    results = {}
    modes = ["direct", "vpn", "tor"]
    
    # We execute checks concurrently
    import asyncio
    tasks = [network_manager.get_public_ip(mode) for mode in modes]
    responses = await asyncio.gather(*tasks)
    
    for mode, res in zip(modes, responses):
        results[mode] = res
        
    return results

@router.post("/config/wireguard")
async def save_wireguard_config(
    config: NetworkConfig,
    current_user: User = Depends(get_current_active_user)
):
    success = network_manager.save_wireguard_config(config.wireguard_config)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration")
    return {"status": "success", "message": "Configuration saved. Please restart the VPN container."}

@router.post("/mode")
async def set_network_mode(
    update: NetworkModeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    current_prefs = dict(current_user.preferences) if current_user.preferences else {}
    current_prefs['network_mode'] = update.mode
    current_user.preferences = current_prefs
    
    # Also validate if mode is valid proxy?
    # For now we trust specific valid values from enum in frontend or service
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return {"status": "success", "mode": update.mode}
