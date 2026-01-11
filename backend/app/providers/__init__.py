from app.providers.amazon_music_provider import AmazonMusicProvider
from app.providers.apple_music_provider import AppleMusicProvider
from app.providers.deezer_provider import DeezerProvider
from app.providers.generic import GenericProvider
from app.providers.manager import provider_manager
from app.providers.soundcloud_provider import SoundCloudProvider
from app.providers.spotify_provider import SpotifyProvider
from app.providers.tidal_provider import TidalProvider
from app.providers.youtube_provider import YouTubeProvider

# Register providers
# In the future we can add more specific providers here
provider_manager.register_provider(GenericProvider())
provider_manager.register_provider(AppleMusicProvider())
provider_manager.register_provider(DeezerProvider())
provider_manager.register_provider(TidalProvider())
provider_manager.register_provider(AmazonMusicProvider())
provider_manager.register_provider(SoundCloudProvider())
provider_manager.register_provider(SpotifyProvider())
provider_manager.register_provider(YouTubeProvider())

__all__ = ["provider_manager"]
