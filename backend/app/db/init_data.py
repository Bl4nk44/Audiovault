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
            
            import hashlib
            # Use the same admin_password for Subsonic (MD5 hashed)
            # nosec B303: MD5 required for Subsonic Legacy Auth
            subsonic_pw_hash = hashlib.md5(admin_password.encode('utf-8')).hexdigest()
            
            user = User(
                email=admin_email,
                username="admin",
                hashed_password=get_password_hash(admin_password),
                subsonic_password=subsonic_pw_hash,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Default admin user created")
            logger.info(f"Admin email: {admin_email}")
            logger.info(f"Subsonic Password (MD5) set to match Admin Password")
        else:
            # Update subsonic password if missing (migration support)
            if not user.subsonic_password:
                import hashlib
                # Default fallback for existing users - sets Subsonic password to 'admin'
                # This is necessary because we cannot recover the plaintext password to hash it with MD5
                default_subsonic_pass = "admin"
                subsonic_pw_hash = hashlib.md5(default_subsonic_pass.encode('utf-8')).hexdigest() # nosec B303
                user.subsonic_password = subsonic_pw_hash
                db.add(user)
                await db.commit()
                logger.info("Updated existing admin with default subsonic password")

            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
