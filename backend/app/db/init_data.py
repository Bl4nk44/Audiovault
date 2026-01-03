from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.core.security import get_password_hash
import logging

logger = logging.getLogger(__name__)

async def init_db(db: AsyncSession) -> None:
    try:
        result = await db.execute(select(User).where(User.username == "admin"))
        user = result.scalars().first()
        
        if not user:
            logger.info("Creating default admin user")
            # Use environment variables for initial setup security
            from app.core.config import settings
            
            admin_email = getattr(settings, "FIRST_SUPERUSER", "admin@example.com")
            # Require password from environment variable for security
            admin_password = getattr(settings, "FIRST_SUPERUSER_PASSWORD", None)
            
            if not admin_password:
                logger.warning("FIRST_SUPERUSER_PASSWORD not set. Creating admin with random password.")
                import secrets
                admin_password = secrets.token_urlsafe(16)
                logger.warning(f"Generated Admin Password: {admin_password}")
            
            user = User(
                email=admin_email,
                username="admin",
                hashed_password=get_password_hash(admin_password),
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Default admin user created")
            logger.info(f"Admin email: {admin_email}")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
