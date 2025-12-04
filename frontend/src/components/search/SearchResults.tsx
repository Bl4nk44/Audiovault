import TrackCard from './TrackCard'
import ArtistCard from './ArtistCard'
import PlaylistCard from './PlaylistCard'
import { motion } from 'framer-motion'

interface SearchResultsProps {
    results: any[]
    isLoading: boolean
}

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.05
        }
    }
}

export default function SearchResults({ results, isLoading }: SearchResultsProps) {
    if (isLoading) {
        return (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                {[...Array(10)].map((_, i) => (
                    <div key={i} className="aspect-[3/4] rounded-2xl bg-white/5 animate-pulse border border-white/5" />
                ))}
            </div>
        )
    }

    if (results.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-20 text-muted-foreground"
            >
                <p className="text-lg">No results found. Try searching for something else.</p>
            </motion.div>
        )
    }

    const artists = results.filter(r => r.type === 'artist')
    const playlists = results.filter(r => r.type === 'playlist')
    const tracks = results.filter(r => !r.type || r.type === 'track' || r.type === 'song')

    return (
        <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-8 pb-20"
        >
            {tracks.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 text-white">Tracks</h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                        {tracks.map((item) => (
                            <TrackCard key={`${item.source}-${item.id}`} track={item} />
                        ))}
                    </div>
                </section>
            )}

            {artists.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 text-white">Artists</h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                        {artists.map((item) => (
                            <ArtistCard key={`${item.source}-${item.id}`} artist={item} />
                        ))}
                    </div>
                </section>
            )}

            {playlists.length > 0 && (
                <section>
                    <h2 className="text-2xl font-bold mb-4 text-white">Playlists</h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                        {playlists.map((item) => (
                            <PlaylistCard key={`${item.source}-${item.id}`} playlist={item} />
                        ))}
                    </div>
                </section>
            )}
        </motion.div>
    )
}
