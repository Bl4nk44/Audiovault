import { useState, useEffect } from 'react'
import APIKeyInput from './APIKeyInput'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import { Save, FolderOpen, Download, Palette, Globe, FileText, Key, User, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import api from '../../services/api'
import AccountSettings from './AccountSettings'

export default function SettingsPanel() {
    const [activeTab, setActiveTab] = useState('general')
    const [settings, setSettings] = useState({
        spotifyClientId: '',
        spotifyClientSecret: '',
        youtubeApiKey: '',
        deezerApiKey: '',
        downloadPath: '/downloads',
        maxParallelDownloads: 3,
        theme: 'dark',
        language: 'en',
        filenameSchema: '{artist} - {title}',
        audioQuality: 'high'
    })
    const [loading, setLoading] = useState(true)
    const [spotifyStatus, setSpotifyStatus] = useState<'idle' | 'loading' | 'valid' | 'invalid'>('idle')
    const [youtubeStatus, setYoutubeStatus] = useState<'idle' | 'loading' | 'valid' | 'invalid'>('idle')

    useEffect(() => {
        fetchSettings()
    }, [])

    // Apply theme immediately on change for preview
    useEffect(() => {
        document.documentElement.className = settings.theme
    }, [settings.theme])

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

    const verifySpotify = async () => {
        if (!settings.spotifyClientId || !settings.spotifyClientSecret) return
        setSpotifyStatus('loading')
        try {
            await api.post('/settings/verify/spotify', {
                clientId: settings.spotifyClientId,
                clientSecret: settings.spotifyClientSecret
            })
            setSpotifyStatus('valid')
            toast.success('Spotify credentials verified!')
        } catch (error) {
            setSpotifyStatus('invalid')
            toast.error('Invalid Spotify credentials')
        }
    }

    const verifyYouTube = async () => {
        if (!settings.youtubeApiKey) return
        setYoutubeStatus('loading')
        try {
            await api.post('/settings/verify/youtube', {
                apiKey: settings.youtubeApiKey
            })
            setYoutubeStatus('valid')
            toast.success('YouTube API Key verified!')
        } catch (error) {
            setYoutubeStatus('invalid')
            toast.error('Invalid YouTube API Key')
        }
    }

    const tabs = [
        { id: 'general', label: 'General', icon: Globe },
        { id: 'account', label: 'Account', icon: User },
        { id: 'appearance', label: 'Appearance', icon: Palette },
        { id: 'files', label: 'Files & Storage', icon: FileText },
        { id: 'integrations', label: 'Integrations', icon: Key },
    ]

    const container = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    }

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    }

    if (loading) return <div className="text-white text-center py-10">Loading settings...</div>

    return (
        <div className="flex flex-col md:flex-row gap-8 pb-20 max-w-6xl">
            {/* Sidebar Tabs */}
            <div className="w-full md:w-64 flex-shrink-0 space-y-2">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === tab.id
                            ? 'bg-primary text-black font-bold shadow-[0_0_15px_rgba(34,197,94,0.4)]'
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <tab.icon size={18} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <motion.div
                key={activeTab}
                variants={container}
                initial="hidden"
                animate="show"
                className="flex-1 space-y-6"
            >
                {activeTab === 'account' && (
                    <AccountSettings />
                )}

                {activeTab === 'general' && (
                    <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">General Preferences</h3>

                        <div className="grid gap-6">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1">Language</label>
                                <select
                                    value={settings.language}
                                    onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                                >
                                    <option value="en">English</option>
                                    <option value="pl">Polish</option>
                                    <option value="de">German</option>
                                    <option value="es">Spanish</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1">Audio Quality</label>
                                <select
                                    value={settings.audioQuality}
                                    onChange={(e) => setSettings({ ...settings, audioQuality: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                                >
                                    <option value="low">Low (128kbps)</option>
                                    <option value="medium">Medium (192kbps)</option>
                                    <option value="high">High (320kbps)</option>
                                    <option value="lossless">Lossless (FLAC)</option>
                                </select>
                            </div>
                        </div>
                    </motion.div>
                )}

                {activeTab === 'appearance' && (
                    <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">Appearance</h3>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {[
                                { id: 'dark', name: 'Default Dark', color: 'bg-[#09090b]' },
                                { id: 'midnight', name: 'Midnight Blue', color: 'bg-[#0f172a]' },
                                { id: 'ocean', name: 'Deep Ocean', color: 'bg-[#0c4a6e]' },
                                { id: 'forest', name: 'Dark Forest', color: 'bg-[#052e16]' },
                                { id: 'sunset', name: 'Sunset Vibes', color: 'bg-[#450a0a]' },
                                { id: 'neon', name: 'Cyber Neon', color: 'bg-[#171717]' },
                            ].map((theme) => (
                                <button
                                    key={theme.id}
                                    onClick={() => setSettings({ ...settings, theme: theme.id })}
                                    className={`relative p-4 rounded-2xl border-2 transition-all overflow-hidden group ${settings.theme === theme.id
                                        ? 'border-primary shadow-[0_0_20px_rgba(34,197,94,0.2)]'
                                        : 'border-white/5 hover:border-white/20'
                                        }`}
                                >
                                    <div className={`absolute inset-0 ${theme.color} opacity-80`} />
                                    <div className="relative z-10 flex flex-col items-center gap-2">
                                        <div className="w-full h-12 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10" />
                                        <span className="font-medium text-white">{theme.name}</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}

                {activeTab === 'files' && (
                    <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">Files & Storage</h3>

                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                                    <FolderOpen size={16} /> Download Path
                                </label>
                                <input
                                    type="text"
                                    value={settings.downloadPath}
                                    onChange={(e) => setSettings({ ...settings, downloadPath: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                                    <FileText size={16} /> Filename Schema
                                </label>
                                <input
                                    type="text"
                                    value={settings.filenameSchema}
                                    onChange={(e) => setSettings({ ...settings, filenameSchema: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50 font-mono text-sm"
                                    placeholder="{user}/{service}/{playlist}/{artist} - {title}"
                                />
                                <p className="text-xs text-gray-500 ml-1 leading-relaxed">
                                    Available tags: <code className="text-primary">{'{artist}'}</code>, <code className="text-primary">{'{title}'}</code>, <code className="text-primary">{'{album}'}</code>, <code className="text-primary">{'{id}'}</code>, <code className="text-primary">{'{year}'}</code>, <code className="text-primary">{'{track_number}'}</code>, <code className="text-primary">{'{playlist}'}</code>, <code className="text-primary">{'{service}'}</code>, <code className="text-primary">{'{user}'}</code>
                                    <br />
                                    Use <code className="text-primary">/</code> to create folders (e.g. <code className="text-gray-300">{'{user}/{service}/{playlist}/{artist} - {title}'}</code>)
                                </p>

                                <div className="mt-2 p-3 rounded-lg bg-black/30 border border-white/5 text-sm text-gray-400 font-mono">
                                    <span className="text-gray-500 uppercase text-xs font-bold mr-2 block mb-1 font-sans">Preview:</span>
                                    <div className="flex items-center gap-2">
                                        <FolderOpen size={14} className="text-yellow-500" />
                                        <span>{settings.downloadPath}</span>
                                    </div>
                                    {settings.filenameSchema.split('/').map((part, index, array) => (
                                        <div key={index} className="flex items-center gap-2 ml-4 border-l border-white/10 pl-2">
                                            {index === array.length - 1 ? <FileText size={14} className="text-blue-400" /> : <FolderOpen size={14} className="text-yellow-500" />}
                                            <span>
                                                {part
                                                    .replace('{artist}', 'The Weeknd')
                                                    .replace('{title}', 'Blinding Lights')
                                                    .replace('{album}', 'After Hours')
                                                    .replace('{id}', '12345')
                                                    .replace('{year}', '2020')
                                                    .replace('{track_number}', '01')
                                                    .replace('{playlist}', 'Top Hits')
                                                    .replace('{service}', 'spotify')
                                                    .replace('{user}', 'mati')
                                                }
                                                {index === array.length - 1 ? '.mp3' : ''}
                                            </span>
                                        </div>
                                    ))}
                                </div>
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
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                                />
                            </div>
                        </div>
                    </motion.div>
                )}

                {activeTab === 'integrations' && (
                    <motion.div variants={item} className="space-y-6 p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl">
                        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">API Integrations</h3>

                        <div className="space-y-6">


                            <div className="space-y-4 pt-4 border-t border-white/5">
                                <div className="flex items-center justify-between">
                                    <h4 className="font-medium text-white flex items-center gap-2">
                                        <span className="w-1.5 h-6 rounded-full bg-green-500" /> Spotify
                                    </h4>
                                    <div className="flex items-center gap-2">
                                        {spotifyStatus === 'loading' && <Loader2 className="animate-spin text-primary" size={18} />}
                                        {spotifyStatus === 'valid' && <CheckCircle className="text-green-500" size={18} />}
                                        {spotifyStatus === 'invalid' && <XCircle className="text-red-500" size={18} />}
                                        <button
                                            onClick={verifySpotify}
                                            className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors"
                                        >
                                            Verify
                                        </button>
                                    </div>
                                </div>
                                <div className="grid gap-4">
                                    <APIKeyInput
                                        label="Client ID"
                                        value={settings.spotifyClientId}
                                        onChange={(v) => {
                                            setSettings({ ...settings, spotifyClientId: v })
                                            setSpotifyStatus('idle')
                                        }}
                                    />
                                    <APIKeyInput
                                        label="Client Secret"
                                        value={settings.spotifyClientSecret}
                                        onChange={(v) => {
                                            setSettings({ ...settings, spotifyClientSecret: v })
                                            setSpotifyStatus('idle')
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="space-y-4 pt-4 border-t border-white/5">
                                <div className="flex items-center justify-between">
                                    <h4 className="font-medium text-white flex items-center gap-2">
                                        <span className="w-1.5 h-6 rounded-full bg-red-500" /> YouTube
                                    </h4>
                                    <div className="flex items-center gap-2">
                                        {youtubeStatus === 'loading' && <Loader2 className="animate-spin text-primary" size={18} />}
                                        {youtubeStatus === 'valid' && <CheckCircle className="text-green-500" size={18} />}
                                        {youtubeStatus === 'invalid' && <XCircle className="text-red-500" size={18} />}
                                        <button
                                            onClick={verifyYouTube}
                                            className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors"
                                        >
                                            Verify
                                        </button>
                                    </div>
                                </div>
                                <APIKeyInput
                                    label="API Key"
                                    value={settings.youtubeApiKey}
                                    onChange={(v) => {
                                        setSettings({ ...settings, youtubeApiKey: v })
                                        setYoutubeStatus('idle')
                                    }}
                                />
                            </div>
                        </div>
                    </motion.div>
                )}

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
        </div >
    )
}
