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
            user = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash("admin"),
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Default admin user created")
            
            logger.info("Credentials: admin / admin")
            logger.warning("Please change the default password immediately!")
            
        else:
            logger.info("Admin user already exists")
            logger.info("Credentials: admin / [HIDDEN]")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
