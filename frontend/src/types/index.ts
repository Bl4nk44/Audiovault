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
    status: 'pending' | 'downloading' | 'completed' | 'failed'
}

export interface WatchlistItem {
    id: string
    source_id: string
    source: string
    type: 'artist' | 'playlist' | 'channel'
    name: string
}
