import TrackCard from './TrackCard'
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

    return (
        <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6 pb-20"
        >
            {results.map((track) => (
                <TrackCard key={`${track.source}-${track.id}`} track={track} />
            ))}
        </motion.div>
    )
}
