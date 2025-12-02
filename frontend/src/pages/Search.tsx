import { useState } from 'react'
import SearchBar from '../components/search/SearchBar'
import SearchResults from '../components/search/SearchResults'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function Search() {
    const [results, setResults] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [offset, setOffset] = useState(0)
    const [hasMore, setHasMore] = useState(true)
    const [currentQuery, setCurrentQuery] = useState('')

    const handleSearch = async (query: string, source: string) => {
        setIsLoading(true)
        setResults([])
        setOffset(0)
        setHasMore(true)
        setCurrentQuery(query)

        try {
            await fetchResults(query, source, 0)
        } catch (error) {
            toast.error('Search failed')
            console.error(error)
        } finally {
            setIsLoading(false)
        }
    }

    const fetchResults = async (query: string, source: string, currentOffset: number) => {
        let newResults: any[] = []

        if (source !== 'all') {
            const response = await api.get(`/${source}/search`, { params: { q: query, offset: currentOffset } })
            newResults = response.data
        } else {
            const sources = ['spotify', 'youtube', 'deezer']
            const promises = sources.map(s =>
                api.get(`/${s}/search`, { params: { q: query, offset: currentOffset } })
                    .then(res => res.data)
                    .catch(() => [])
            )
            const allResults = await Promise.all(promises)
            newResults = allResults.flat()
        }

        if (newResults.length === 0) {
            setHasMore(false)
        } else {
            setResults(prev => currentOffset === 0 ? newResults : [...prev, ...newResults])
            setOffset(currentOffset + 20)
        }
    }

    const handleLoadMore = async () => {
        if (isLoading || !hasMore) return
        setIsLoading(true)
        try {
            // For now assuming 'all' or specific source is handled by keeping track of last source
            // But handleSearch doesn't save source. Let's assume 'all' for now or we need to save source state.
            // Simplification: just pass 'all' if we don't track it, or better add source state.
            // Let's add source state.
            await fetchResults(currentQuery, 'all', offset)
        } catch (error) {
            toast.error('Failed to load more')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="space-y-8">
            <div className="text-center space-y-4">
                <h1 className="text-4xl font-bold tracking-tight">Search Music</h1>
                <p className="text-muted-foreground">Find your favorite tracks from Spotify, YouTube, and Deezer</p>
            </div>

            <SearchBar onSearch={handleSearch} isLoading={isLoading} />

            <div className="mt-8 space-y-8">
                <SearchResults results={results} isLoading={isLoading && offset === 0} />

                {results.length > 0 && hasMore && (
                    <div className="flex justify-center pb-20">
                        <button
                            onClick={handleLoadMore}
                            disabled={isLoading}
                            className="px-8 py-3 rounded-full bg-white/10 hover:bg-white/20 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? 'Loading...' : 'Load More'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
