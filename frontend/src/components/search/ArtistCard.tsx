import { Plus, Check, User } from 'lucide-react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import { useState } from 'react'

interface Artist {
    id: string
    name: string
    image_url: string | null
    source: 'spotify' | 'youtube' | 'deezer'
}

interface ArtistCardProps {
    artist: Artist
}

export default function ArtistCard({ artist }: ArtistCardProps) {
    const [isAdded, setIsAdded] = useState(false)
    const [imageError, setImageError] = useState(false)

    const handleAddToWatchlist = async (e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await api.post('/watchlist/add', {
                watch_type: 'artist',
                source: artist.source,
                source_id: artist.id,
                source_name: artist.name,
                image_url: artist.image_url,
                auto_download: true // Default to true for convenience
            })
            setIsAdded(true)
            toast.success('Artist added to watchlist')
        } catch (error) {
            toast.error('Failed to add to watchlist')
        }
    }

    return (
        <motion.div
            whileHover={{ scale: 1.02, backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
            className="group relative flex flex-col items-center p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-all cursor-pointer"
        >
            <div className="relative w-32 h-32 rounded-full overflow-hidden shadow-lg group-hover:shadow-primary/20 transition-all mb-4">
                {artist.image_url && !imageError ? (
                    <img
                        src={artist.image_url}
                        alt={artist.name}
                        className="w-full h-full object-cover"
                        onError={() => setImageError(true)}
                    />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                        <User className="text-gray-600" size={40} />
                    </div>
                )}
            </div>

            <h3 className="font-bold text-white text-center truncate w-full group-hover:text-primary transition-colors">{artist.name}</h3>
            <p className="text-sm text-gray-400 capitalize">{artist.source}</p>

            <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={handleAddToWatchlist}
                disabled={isAdded}
                className={`mt-3 p-2 rounded-full transition-colors ${isAdded ? 'bg-green-500 text-black' : 'bg-white/10 text-white hover:bg-primary hover:text-black'
                    }`}
                title={isAdded ? "Added" : "Add to Watchlist"}
            >
                {isAdded ? <Check size={20} /> : <Plus size={20} />}
            </motion.button>
        </motion.div>
    )
}
