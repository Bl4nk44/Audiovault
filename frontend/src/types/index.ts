export interface User {
    id: string
    email: string
    username: string
    preferences: any
}

export interface Track {
    id: string
    title: string
    artist: string
    cover?: string
    source: string
    duration?: number
    album?: string
    filename?: string
}

export interface Download {
    id: string
    track: Track
    progress: number
    status: 'pending' | 'downloading' | 'completed' | 'failed' | 'paused'
    error?: string
    retry_count?: number
}

export interface WatchlistItem {
    id: string
    source_id: string
    source: string
    type: 'artist' | 'playlist' | 'channel'
    name: string
    metadata?: {
        image_url?: string
    }
}

export interface Album {
    id: string
    title: string
    release_date?: string
    images?: Record<string, any>
    artist_id: string
}

export interface Artist {
    id: string
    name: string
    bio?: string
    spotify_id?: string
    deezer_id?: string
    images?: Record<string, any>
    albums?: Album[]
    tracks?: Track[]
}
