import logging

from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


async def init_db(db: AsyncSession) -> None:
    try:
        from app.core.config import settings

        admin_username = getattr(settings, "ADMIN_USERNAME", "admin")
        admin_email = getattr(settings, "ADMIN_EMAIL", "admin@example.com")

        result = await db.execute(select(User).where((User.email == admin_email) | (User.username == admin_username)))
        user = result.scalars().first()

        if not user:
            logger.info("Creating default admin user")
            # Require password from environment variable for security
            admin_password = getattr(settings, "ADMIN_PASSWORD", None)

            if not admin_password:
                logger.warning("ADMIN_PASSWORD not set. Creating admin with random password.")
                import secrets

                admin_password = secrets.token_urlsafe(16)
                # Password is NOT logged for security reasons. 
                # User should set ADMIN_PASSWORD in .env for production.

            user = User(
                email=admin_email,
                username=admin_username,
                hashed_password=get_password_hash(admin_password),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Default admin user created")
            logger.info(f"Admin username: {admin_username}")
            
            # Mask email for privacy
            masked_email = f"{admin_email[0]}***@{admin_email.split('@')[-1]}" if "@" in admin_email else "***"
            logger.info(f"Admin email: {masked_email}")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
        await db.rollback()
