from app.providers.manager import provider_manager
from app.providers.generic import GenericProvider

# Register providers
# In the future we can add more specific providers here
provider_manager.register_provider(GenericProvider())

__all__ = ["provider_manager"]
