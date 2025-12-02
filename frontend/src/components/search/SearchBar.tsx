import { Search as SearchIcon, X, Filter } from 'lucide-react'
import { useState } from 'react'
import { motion } from 'framer-motion'


interface SearchBarProps {
    onSearch: (query: string, source: string) => void
    isLoading: boolean
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [source, setSource] = useState('all')

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (query.trim()) {
            onSearch(query, source)
        }
    }

    return (
        <div className="w-full max-w-4xl mx-auto mb-12 relative z-10">
            <motion.form
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                onSubmit={handleSubmit}
                className="relative flex flex-col md:flex-row items-center gap-4"
            >
                <div className="relative flex-1 w-full group">
                    <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
                    <SearchIcon className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-primary transition-colors" size={22} />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="What do you want to listen to?"
                        className="w-full pl-14 pr-12 py-5 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 text-white placeholder:text-gray-500 focus:outline-none focus:border-primary/50 focus:bg-white/10 transition-all shadow-xl text-lg"
                    />
                    {query && (
                        <button
                            type="button"
                            onClick={() => setQuery('')}
                            className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                        >
                            <X size={20} />
                        </button>
                    )}
                </div>

                <div className="flex gap-4 w-full md:w-auto">
                    <div className="relative min-w-[140px]">
                        <select
                            value={source}
                            onChange={(e) => setSource(e.target.value)}
                            className="w-full appearance-none px-6 py-5 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 text-white font-medium focus:outline-none focus:border-primary/50 cursor-pointer hover:bg-white/10 transition-all"
                        >
                            <option value="all" className="bg-gray-900">All Sources</option>
                            <option value="spotify" className="bg-gray-900">Spotify</option>
                            <option value="youtube" className="bg-gray-900">YouTube</option>
                            <option value="deezer" className="bg-gray-900">Deezer</option>
                        </select>
                        <Filter className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={18} />
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        type="submit"
                        disabled={isLoading}
                        className="px-10 py-5 rounded-2xl bg-primary text-black font-bold shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] transition-all disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap"
                    >
                        {isLoading ? 'Searching...' : 'Search'}
                    </motion.button>
                </div>
            </motion.form>

            {/* Quick Filters */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="flex flex-wrap gap-3 mt-6 justify-center"
            >
                {['Rock', 'Pop', 'Hip-Hop', 'Electronic', 'Indie', 'Jazz', 'Classical'].map((genre, i) => (
                    <motion.button
                        key={genre}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.4 + (i * 0.05) }}
                        whileHover={{ scale: 1.1, backgroundColor: "rgba(255, 255, 255, 0.15)" }}
                        whileTap={{ scale: 0.95 }}
                        className="px-5 py-2 rounded-full bg-white/5 border border-white/5 text-sm font-medium text-gray-300 hover:text-white hover:border-white/20 transition-all backdrop-blur-sm"
                    >
                        {genre}
                    </motion.button>
                ))}
            </motion.div>
        </div>
    )
}
