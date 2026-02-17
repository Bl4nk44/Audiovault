# 👥 Product Context: User & Market

## User Personas

### 1. Alex - The Audiophile
**Demographics**
- Age: 28-45
- Tech-savvy, runs home server (NAS, Docker)
- Budget: $50-200/month on music subscriptions

**Pain Points**
- Streaming services compress audio quality
- Can't access music offline reliably
- Wants lossless FLAC files
- Frustrated by platform lock-in

**Goals**
- Build high-quality local music library
- Maintain streaming convenience
- Preserve music independent of subscription status

**How Audiovault Helps**
- FLAC download support
- Subsonic API for mobile streaming
- Automated synchronization
- Multi-platform import

### 2. Maria - The Digital Archivist
**Demographics**
- Age: 22-35
- Collects and organizes media
- Active in r/datahoarder community

**Pain Points**
- Services delete content without notice
- Geo-restrictions on certain tracks
- Wants permanent ownership
- Needs metadata preservation

**Goals**
- Archive entire playlists permanently
- Organize by service and playlist structure
- Never lose access to favorite tracks

**How Audiovault Helps**
- Hierarchical library organization
- Robust fallback for geo-blocked content
- ID3 tag management
- Automated backup workflows

### 3. Sam - The Multi-Platform User
**Demographics**
- Age: 18-30
- Uses Spotify, YouTube, SoundCloud
- Frustrated by fragmentation

**Pain Points**
- Playlists scattered across platforms
- Can't consolidate music library
- Paying multiple subscriptions
- Limited cross-platform compatibility

**Goals**
- Unify all playlists in one place
- Access everything from one app
- Reduce subscription costs

**How Audiovault Helps**
- Import from 7+ platforms
- Universal search across services
- Single self-hosted library
- Mobile access via Subsonic clients

## User Journey

### Discovery Phase
1. User searches for "self-hosted Spotify alternative"
2. Finds Audiovault on Reddit/GitHub
3. Reviews features and documentation

### Setup Phase
1. Clones repository
2. Configures .env file with API keys
3. Runs Docker Compose
4. Creates admin account

### Onboarding Phase
1. Connects streaming service accounts
2. Imports first playlist
3. Watches download progress in real-time
4. Configures quality preferences

### Active Use Phase
1. Adds playlists to watchlist
2. Auto-sync runs every 60 minutes
3. Browses library by service/playlist
4. Streams to mobile via Subsonic

### Power User Phase
1. Configures Last.fm scrobbling
2. Uses API for custom integrations
3. Contributes to codebase
4. Shares workflows with community

## Market Context

### Competitors
- **Lidarr**: Music collection manager (no direct downloads)
- **Navidrome**: Subsonic server only (no import)
- **Soulseek**: P2P, no streaming integration
- **yt-dlp**: CLI tool, no web UI

### Competitive Advantages
- Only solution combining import + library + streaming
- Modern, beautiful UI vs dated competitors
- Active development and community
- Docker-first deployment

### Market Trends
- Growing self-hosted movement (privacy concerns)
- Dissatisfaction with streaming service changes
- Increased home lab adoption
- Docker/containerization mainstream
