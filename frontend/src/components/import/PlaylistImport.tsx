import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, Download, Music, List } from 'lucide-react';
import Button from '../ui/Button';
import { importApi } from '../../api/import';
import type { PlaylistMetadata } from '../../api/import';
import toast from 'react-hot-toast';
import { useStore } from '../../store/useStore';
import { downloadsApi } from '../../api/downloads';

export default function PlaylistImport() {
    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [previewData, setPreviewData] = useState<PlaylistMetadata | null>(null);
    const { fetchDownloads } = useStore();
    const [isImporting, setIsImporting] = useState(false);
    const [importedCount, setImportedCount] = useState(0);

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url.trim()) return;

        setIsLoading(true);
        setPreviewData(null);
        try {
            const data = await importApi.importPlaylist(url);
            setPreviewData(data);
            if (data.tracks.length === 0) {
                toast.error('No tracks found in this playlist.');
            } else {
                toast.success(`Found ${data.tracks.length} tracks!`);
            }
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to extract playlist.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleImport = async () => {
        if (!previewData || previewData.tracks.length === 0) return;

        setIsImporting(true);
        setImportedCount(0);

        let successCount = 0;

        // Process tracks sequentially or in small batches to avoid flooding
        // For now, sequential to show progress
        for (const track of previewData.tracks) {
            try {
                // We map generalized metadata to Spotizerr conventions
                // Source is 'generic' or 'youtube' depending on what we want.
                // But download_manager resolves based on Source.
                // If it's a URL, we might want source='generic' or detect from URL?
                // Actually, our download manager expects 'youtube' or 'spotify' or 'yt_search'

                // For generic import, we primarily want to SEARCH youtube.
                // So we can use source='spotify' (which triggers search) OR add a new 'search' source.
                // But wait, download_manager.py line 341 handles 'spotify' by searching.
                // Let's rely on 'youtube' source if we have a direct ID (not common for generic), 
                // OR 'generic' which we should handle in download_manager?

                // Strategy: We will treat these imports as "search queries".
                // We'll queue them using a specific format that our backend can handle.
                // Since our backend's add_download expects a track_id, we'll pass the search query as track_id
                // and use 'spotify' as source which triggers a search in _resolve_url.
                // In the future, we should probably add a dedicated 'search' source.

                // Resolving metadata into entities (Generic -> Track Entity)
                const resolvedTrack = await importApi.resolve(track);

                await downloadsApi.add({
                    track_id: resolvedTrack.id,
                    source: 'imported',
                    playlist_name: previewData.title
                });

                successCount++;
                setImportedCount(successCount);
            } catch (error) {
                console.error('Failed to queue track:', track.title);
            }
        }

        setIsImporting(false);
        toast.success(`Successfully queued ${successCount} tracks.`);
        setUrl('');
        setPreviewData(null);
        fetchDownloads(); // Refresh queue
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto p-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center space-y-4"
            >
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                    Import Playlist
                </h1>
                <p className="text-muted-foreground text-lg">
                    Supports Tidal, SoundCloud, Bandcamp, Apple Music, and more.
                </p>
            </motion.div>

            {/* Input Section */}
            <motion.div
                className="bg-card/50 backdrop-blur rounded-xl p-6 border border-white/5 shadow-xl"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1 }}
            >
                <form onSubmit={handleAnalyze} className="flex gap-4 flex-col sm:flex-row">
                    <div className="relative flex-1">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Search className="h-5 w-5 text-muted-foreground" />
                        </div>
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="Paste playlist URL here..."
                            className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-lg bg-black/50 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                            required
                        />
                    </div>
                    <Button
                        type="submit"
                        isLoading={isLoading}
                        size="lg"
                        className="w-full sm:w-auto min-w-[120px]"
                    >
                        {isLoading ? 'Analyzing...' : 'Analyze'}
                    </Button>
                </form>
            </motion.div>

            {/* Preview Section */}
            <AnimatePresence>
                {previewData && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-6"
                    >
                        <div className="flex items-center justify-between bg-white/5 rounded-xl p-6 border border-white/10">
                            <div className="space-y-1">
                                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                                    <List className="w-6 h-6 text-green-500" />
                                    {previewData.title}
                                </h2>
                                <p className="text-muted-foreground">
                                    Found {previewData.tracks.length} tracks • {previewData.author || "Unknown Author"}
                                </p>
                            </div>
                            <Button
                                onClick={handleImport}
                                disabled={isImporting}
                                size="lg"
                                className="bg-green-600 hover:bg-green-700"
                            >
                                {isImporting ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Queuing...
                                    </>
                                ) : (
                                    <>
                                        <Download className="w-5 h-5 mr-2" />
                                        Import All
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* Progress Bar */}
                        {isImporting && (
                            <div className="space-y-2 bg-card rounded-lg p-4 border border-white/5">
                                <div className="flex justify-between text-sm">
                                    <span>Importing tracks...</span>
                                    <span>{Math.round((importedCount / previewData.tracks.length) * 100)}%</span>
                                </div>
                                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-green-500"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(importedCount / previewData.tracks.length) * 100}%` }}
                                        transition={{ duration: 0.3 }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground text-center">
                                    {importedCount} / {previewData.tracks.length} tracks queued
                                </p>
                            </div>
                        )}

                        <div className="grid gap-3">
                            {previewData.tracks.slice(0, 100).map((track, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.03 }}
                                    className="flex items-center gap-4 bg-card/40 p-3 rounded-lg border border-white/5 hover:bg-white/5 transition-colors group"
                                >
                                    <div className="w-10 h-10 rounded bg-white/10 flex items-center justify-center flex-shrink-0">
                                        {track.image_url ? (
                                            <img src={track.image_url} alt="" className="w-full h-full object-cover rounded" />
                                        ) : (
                                            <Music className="w-5 h-5 text-muted-foreground" />
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h4 className="font-medium text-white truncate">{track.title}</h4>
                                        <p className="text-sm text-muted-foreground truncate">{track.artist}</p>
                                    </div>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                        <span className="text-xs text-muted-foreground">{track.duration_ms ? `${Math.floor(track.duration_ms / 1000 / 60)}:${String(Math.floor(track.duration_ms / 1000 % 60)).padStart(2, '0')}` : ''}</span>
                                    </div>
                                </motion.div>
                            ))}
                            {previewData.tracks.length > 100 && (
                                <p className="text-center text-muted-foreground py-4">
                                    ...and {previewData.tracks.length - 100} more
                                </p>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
