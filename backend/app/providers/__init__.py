from app.providers.manager import provider_manager
from app.providers.generic import GenericProvider

# Register providers
# In the future we can add more specific providers here
provider_manager.register_provider(GenericProvider())
from app.providers.apple_music_provider import AppleMusicProvider
from app.providers.deezer_provider import DeezerProvider

provider_manager.register_provider(AppleMusicProvider())
provider_manager.register_provider(DeezerProvider())
from app.providers.tidal_provider import TidalProvider
provider_manager.register_provider(TidalProvider())
from app.providers.amazon_music_provider import AmazonMusicProvider
provider_manager.register_provider(AmazonMusicProvider())
from app.providers.soundcloud_provider import SoundCloudProvider
provider_manager.register_provider(SoundCloudProvider())
from app.providers.spotify_provider import SpotifyProvider
provider_manager.register_provider(SpotifyProvider())
from app.providers.youtube_provider import YouTubeProvider
provider_manager.register_provider(YouTubeProvider())

__all__ = ["provider_manager"]
