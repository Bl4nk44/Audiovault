import { useState, useEffect } from 'react'
import APIKeyInput from './APIKeyInput'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import { Save, FolderOpen, Download } from 'lucide-react'
import api from '../../services/api'

export default function SettingsPanel() {
    const [settings, setSettings] = useState({
        spotifyClientId: '',
        spotifyClientSecret: '',
        youtubeApiKey: '',
        deezerApiKey: '',
        downloadPath: '/downloads',
        maxParallelDownloads: 3
    })
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        try {
            const response = await api.get('/settings/')
            setSettings(prev => ({ ...prev, ...response.data }))
        } catch (error) {
            console.error('Failed to fetch settings:', error)
            toast.error('Failed to load settings')
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        try {
            await api.post('/settings/', settings)
            toast.success('Settings saved successfully')
        } catch (error) {
            console.error('Failed to save settings:', error)
            toast.error('Failed to save settings')
        }
    }

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    }

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    }

    if (loading) {
        return <div className="text-white text-center py-10">Loading settings...</div>
    }

    return (
        <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-8 max-w-3xl pb-20"
        >
            <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 flex items-center gap-3">
                    <span className="w-2 h-8 rounded-full bg-primary" />
                    Spotify Integration
                </h3>

                <div className="grid gap-6">
                    <APIKeyInput
                        label="Client ID"
                        value={settings.spotifyClientId}
                        onChange={(v) => setSettings({ ...settings, spotifyClientId: v })}
                        placeholder="Enter your Spotify Client ID"
                    />
                    <APIKeyInput
                        label="Client Secret"
                        value={settings.spotifyClientSecret}
                        onChange={(v) => setSettings({ ...settings, spotifyClientSecret: v })}
                        placeholder="Enter your Spotify Client Secret"
                    />
                </div>

                <p className="text-sm text-gray-400 pl-2 border-l-2 border-white/10">
                    Get your credentials from the <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer" className="text-primary hover:text-primary/80 hover:underline transition-colors font-medium">Spotify Developer Dashboard</a>.
                </p>
            </motion.div>

            <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 flex items-center gap-3">
                    <span className="w-2 h-8 rounded-full bg-red-500" />
                    YouTube Integration
                </h3>

                <APIKeyInput
                    label="API Key"
                    value={settings.youtubeApiKey}
                    onChange={(v) => setSettings({ ...settings, youtubeApiKey: v })}
                    placeholder="Enter your YouTube Data API Key"
                />
            </motion.div>

            <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 flex items-center gap-3">
                    <span className="w-2 h-8 rounded-full bg-blue-500" />
                    Download Settings
                </h3>

                <div className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                            <FolderOpen size={16} /> Download Path
                        </label>
                        <input
                            type="text"
                            value={settings.downloadPath}
                            onChange={(e) => setSettings({ ...settings, downloadPath: e.target.value })}
                            className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/40 transition-all"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                            <Download size={16} /> Max Parallel Downloads
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="10"
                            value={settings.maxParallelDownloads}
                            onChange={(e) => setSettings({ ...settings, maxParallelDownloads: parseInt(e.target.value) })}
                            className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/40 transition-all"
                        />
                    </div>
                </div>
            </motion.div>

            <motion.div variants={item} className="flex justify-end pt-4">
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleSave}
                    className="flex items-center gap-2 bg-primary text-black font-bold px-8 py-4 rounded-xl shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] transition-all"
                >
                    <Save size={20} />
                    Save Changes
                </motion.button>
            </motion.div>
        </motion.div>
    )
}
