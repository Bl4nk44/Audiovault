"""Global application settings (shared across all users), stored in the app_settings table.

No Redis caching: reads happen on rare, rate-limited paths (registration / admin toggle),
so a plain DB read keeps the code simple and avoids cache-coherency issues.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.app_setting import AppSetting

REGISTRATION_ENABLED_KEY = "registration_enabled"


async def get_bool_setting(db: AsyncSession, key: str, default: bool) -> bool:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        return default
    return row.value == "true"


async def set_bool_setting(db: AsyncSession, key: str, value: bool) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    str_value = "true" if value else "false"
    if row is None:
        db.add(AppSetting(key=key, value=str_value))
    else:
        row.value = str_value
    await db.commit()


async def is_registration_enabled(db: AsyncSession) -> bool:
    """Effective registration state.

    The env kill-switch (settings.REGISTRATION_ENABLED) can only restrict: when it
    is false, registration is off regardless of the runtime DB toggle. Otherwise the
    DB toggle decides (enabled by default when no row exists).
    """
    if not settings.REGISTRATION_ENABLED:
        return False
    return await get_bool_setting(db, REGISTRATION_ENABLED_KEY, default=True)


async def set_registration_enabled(db: AsyncSession, enabled: bool) -> None:
    await set_bool_setting(db, REGISTRATION_ENABLED_KEY, enabled)
