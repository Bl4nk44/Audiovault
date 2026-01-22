"""
Service for managing encrypted credentials.
Provides methods to encrypt/decrypt credentials and migrate existing data.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encryption_service
from app.models.credentials import ServiceCredentials

logger = logging.getLogger(__name__)


class CredentialsService:
    """
    Service for managing service credentials with encryption.
    """

    @staticmethod
    async def store_tokens(
        db: AsyncSession,
        user_id: UUID,
        service: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at=None,
        extra_data: Optional[dict] = None,
    ) -> ServiceCredentials:
        """
        Store encrypted tokens for a service.

        Args:
            db: Database session
            user_id: User ID
            service: Service name (spotify, youtube, deezer)
            access_token: Access token to encrypt
            refresh_token: Optional refresh token to encrypt
            expires_at: Token expiration time
            extra_data: Additional data to store

        Returns:
            ServiceCredentials instance
        """
        # Encrypt tokens
        encrypted_access = encryption_service.encrypt(access_token)
        encrypted_refresh = None
        if refresh_token:
            encrypted_refresh = encryption_service.encrypt(refresh_token)

        # Check if credentials exist
        result = await db.execute(
            select(ServiceCredentials).where(
                ServiceCredentials.user_id == user_id,
                ServiceCredentials.service == service,
            )
        )
        creds = result.scalar_one_or_none()

        if creds:
            # Update existing
            creds.access_token = encrypted_access
            creds.refresh_token = encrypted_refresh
            creds.expires_at = expires_at
            if extra_data:
                creds.extra_data = extra_data
        else:
            # Create new
            creds = ServiceCredentials(
                user_id=user_id,
                service=service,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                expires_at=expires_at,
                extra_data=extra_data or {},
            )
            db.add(creds)

        await db.commit()
        await db.refresh(creds)

        logger.info(f"Stored encrypted credentials for {service} user {user_id}")
        return creds

    @staticmethod
    async def get_tokens(
        db: AsyncSession,
        user_id: UUID,
        service: str,
    ) -> Optional[dict]:
        """
        Get decrypted tokens for a service.

        Returns:
            Dict with access_token, refresh_token, expires_at, extra_data
            or None if not found
        """
        result = await db.execute(
            select(ServiceCredentials).where(
                ServiceCredentials.user_id == user_id,
                ServiceCredentials.service == service,
            )
        )
        creds = result.scalar_one_or_none()

        if not creds:
            return None

        try:
            access_token = encryption_service.decrypt(creds.access_token) if creds.access_token else None
            refresh_token = encryption_service.decrypt(creds.refresh_token) if creds.refresh_token else None

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": creds.expires_at,
                "extra_data": creds.extra_data or {},
            }
        except ValueError as e:
            logger.error(f"Failed to decrypt credentials for {service}: {e}")
            return None

    @staticmethod
    async def migrate_unencrypted_credentials(db: AsyncSession) -> dict:
        """
        Migrate existing unencrypted credentials to encrypted format.

        Returns:
            Dict with migration statistics
        """
        result = await db.execute(select(ServiceCredentials))
        all_creds = result.scalars().all()

        migrated = 0
        already_encrypted = 0
        failed = 0

        for creds in all_creds:
            try:
                # Check if access_token is already encrypted
                if creds.access_token and not encryption_service.is_encrypted(creds.access_token):
                    creds.access_token = encryption_service.encrypt(creds.access_token)
                    migrated += 1
                else:
                    already_encrypted += 1

                # Check refresh_token
                if creds.refresh_token and not encryption_service.is_encrypted(creds.refresh_token):
                    creds.refresh_token = encryption_service.encrypt(creds.refresh_token)

            except Exception as e:
                logger.error(f"Failed to migrate credentials {creds.id}: {e}")
                failed += 1

        await db.commit()

        logger.info(f"Credentials migration: {migrated} migrated, {already_encrypted} already encrypted, {failed} failed")

        return {
            "migrated": migrated,
            "already_encrypted": already_encrypted,
            "failed": failed,
            "total": len(all_creds),
        }

    @staticmethod
    async def delete_credentials(
        db: AsyncSession,
        user_id: UUID,
        service: str,
    ) -> bool:
        """Delete credentials for a specific service."""
        result = await db.execute(
            select(ServiceCredentials).where(
                ServiceCredentials.user_id == user_id,
                ServiceCredentials.service == service,
            )
        )
        creds = result.scalar_one_or_none()

        if creds:
            await db.delete(creds)
            await db.commit()
            return True

        return False


# Singleton instance
credentials_service = CredentialsService()
