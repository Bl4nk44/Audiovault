import { useRef, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useStore } from '../../store/useStore'
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Maximize2, X, Activity } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

export default function Player() {
    const { currentTrack, isPlaying, togglePlay, volume, setVolume } = useStore()
    const audioRef = useRef<HTMLAudioElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [isExpanded, setIsExpanded] = useState(false)
    const [showVisualizer, setShowVisualizer] = useState(true)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const hasRecordedRef = useRef(false)

    // Reset recording flag on track change
    useEffect(() => {
        hasRecordedRef.current = false
    }, [currentTrack])

    // Record history
    useEffect(() => {
        if (currentTime > 30 && !hasRecordedRef.current && currentTrack) {
            hasRecordedRef.current = true
            // Fire and forget
            import('../../services/api').then(module => {
                module.default.post('/history/record', {
                    track_id: currentTrack.id,
                    duration_played: 30
                }).catch(err => console.error("Failed to record history", err))
            })
        }
    }, [currentTime, currentTrack])

    const audioContextRef = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)
    const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
    const [imgError, setImgError] = useState(false)

    // Reset image error on track change
    useEffect(() => {
        setImgError(false)
    }, [currentTrack])

    // Audio Context & Visualizer
    useEffect(() => {
        if (!audioRef.current || !canvasRef.current) return

        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        let animationId: number

        const initAudio = async () => {
            try {
                if (!audioContextRef.current) {
                    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
                    audioContextRef.current = new AudioContextClass()
                    analyserRef.current = audioContextRef.current.createAnalyser()
                    analyserRef.current.fftSize = 256

                    // Connect source only once
                    if (audioRef.current && !sourceRef.current) {
                        sourceRef.current = audioContextRef.current.createMediaElementSource(audioRef.current)
                        sourceRef.current.connect(analyserRef.current)
                        analyserRef.current.connect(audioContextRef.current.destination)
                    }
                }

                // Resume context if suspended (browser policy)
                if (audioContextRef.current.state === 'suspended') {
                    await audioContextRef.current.resume()
                }

                const analyser = analyserRef.current
                if (!analyser) return

                const bufferLength = analyser.frequencyBinCount
                const dataArray = new Uint8Array(bufferLength)

                const draw = () => {
                    animationId = requestAnimationFrame(draw)
                    analyser.getByteFrequencyData(dataArray)

                    ctx.clearRect(0, 0, canvas.width, canvas.height)

                    // Ambient Wave Effect
                    const width = canvas.width
                    const height = canvas.height
                    const barWidth = (width / bufferLength) * 2.5

                    // Create gradient based on frequency intensity
                    const average = dataArray.reduce((a, b) => a + b) / dataArray.length

                    // Dynamic background tint based on bass
                    ctx.fillStyle = `rgba(20, 0, 40, ${average / 255 * 0.2})`
                    ctx.fillRect(0, 0, width, height)

                    let x = 0

                    ctx.beginPath()
                    ctx.moveTo(0, height)

                    for (let i = 0; i < bufferLength; i++) {
                        const barHeight = (dataArray[i] / 255) * height * 0.8 // Increased height multiplier

                        // Smooth curve
                        const y = height - barHeight

                        if (i === 0) {
                            ctx.moveTo(x, y)
                        } else {
                            const prevX = x - barWidth
                            const prevY = height - ((dataArray[i - 1] / 255) * height * 0.5)
                            const cpX = (prevX + x) / 2
                            const cpY = (prevY + y) / 2
                            ctx.quadraticCurveTo(cpX, cpY, x, y)
                        }

                        x += barWidth
                    }

                    ctx.lineTo(width, height)
                    ctx.lineTo(0, height)
                    ctx.closePath()

                    const gradient = ctx.createLinearGradient(0, height * 0.5, 0, height)
                    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.8)') // Green top (more visible)
                    gradient.addColorStop(0.5, 'rgba(168, 85, 247, 0.6)') // Purple middle
                    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.4)') // Blue bottom

                    ctx.fillStyle = gradient
                    ctx.fill()
                }
                draw()
            } catch (e) {
                console.error("Audio context error:", e)
            }
        }

        // Initialize on play if not already
        if (isPlaying) {
            initAudio()
        }

        return () => {
            if (animationId) cancelAnimationFrame(animationId)
        }
    }, [isPlaying, showVisualizer])

    // Playback Control
    useEffect(() => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.play().catch(e => console.error("Play error:", e))
            } else {
                audioRef.current.pause()
            }
        }
    }, [isPlaying, currentTrack])

    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = volume
        }
    }, [volume])

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime)
            setDuration(audioRef.current.duration || 0)
        }
    }

    const formatTime = (time: number) => {
        if (isNaN(time)) return "0:00"
        const minutes = Math.floor(time / 60)
        const seconds = Math.floor(time % 60)
        return `${minutes}:${seconds.toString().padStart(2, '0')}`
    }

    if (!currentTrack) return null

    // Construct stream URL
    // Use filename if available (for downloads), otherwise fallback to ID (might not work if file has extension)
    // Ideally backend should handle ID lookup if filename is missing, but filename is safer.
    const streamUrl = currentTrack.filename
        ? `${import.meta.env.VITE_API_URL}/stream/${encodeURIComponent(currentTrack.filename)}`
        : `${import.meta.env.VITE_API_URL}/stream/${currentTrack.id}.mp3`

    return (
        <motion.div
            initial={{ y: 100 }}
            animate={{ y: 0 }}
            exit={{ y: 100 }}
            className={cn(
                "fixed bottom-0 left-0 right-0 z-50 transition-all duration-500 ease-in-out",
                isExpanded ? "h-screen bg-black/90 backdrop-blur-3xl" : "h-24 bg-black/60 backdrop-blur-xl border-t border-white/10"
            )}
        >
            {/* Global Visualizer Background */}
            {showVisualizer && createPortal(
                <canvas
                    ref={canvasRef}
                    width={window.innerWidth}
                    height={window.innerHeight}
                    className="fixed inset-0 w-full h-full pointer-events-none z-[5] opacity-80 mix-blend-screen"
                />,
                document.body
            )}

            <div className={cn("container mx-auto h-full flex flex-col", isExpanded ? "justify-center p-8" : "flex-row items-center justify-between px-4")}>

                {/* Track Info */}
                <div className={cn("flex items-center gap-4 transition-all", isExpanded ? "flex-col text-center mb-8" : "w-1/3")}>
                    <div className={cn("relative overflow-hidden rounded-xl shadow-2xl", isExpanded ? "w-64 h-64 mb-4" : "w-14 h-14")}>
                        {currentTrack.cover && !imgError ? (
                            <img
                                src={currentTrack.cover}
                                alt={currentTrack.title}
                                className="w-full h-full object-cover"
                                onError={() => setImgError(true)}
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                                <span className="text-2xl">🎵</span>
                            </div>
                        )}
                    </div>
                    <div>
                        <h3 className={cn("font-bold text-white truncate", isExpanded ? "text-3xl" : "text-base")}>{currentTrack.title}</h3>
                        <p className={cn("text-gray-400 truncate", isExpanded ? "text-xl" : "text-xs")}>{currentTrack.artist}</p>
                    </div>
                </div>

                {/* Controls */}
                <div className={cn("flex flex-col items-center gap-2", isExpanded ? "w-full max-w-lg mx-auto" : "flex-1")}>
                    <div className="flex items-center gap-6">
                        <button className="text-gray-400 hover:text-white transition-colors">
                            <SkipBack size={isExpanded ? 32 : 24} />
                        </button>
                        <button
                            onClick={togglePlay}
                            className={cn("rounded-full bg-primary text-black flex items-center justify-center hover:scale-105 transition-all shadow-[0_0_15px_rgba(34,197,94,0.5)]", isExpanded ? "w-16 h-16" : "w-10 h-10")}
                        >
                            {isPlaying ? <Pause size={isExpanded ? 32 : 20} fill="currentColor" /> : <Play size={isExpanded ? 32 : 20} fill="currentColor" className="ml-1" />}
                        </button>
                        <button className="text-gray-400 hover:text-white transition-colors">
                            <SkipForward size={isExpanded ? 32 : 24} />
                        </button>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full flex items-center gap-3 text-xs text-gray-400 font-medium">
                        <span>{formatTime(currentTime)}</span>
                        <div className="flex-1 h-1 bg-white/10 rounded-full cursor-pointer group relative">
                            <div
                                className="absolute top-0 left-0 h-full bg-primary rounded-full group-hover:bg-green-400 transition-colors"
                                style={{ width: `${(currentTime / duration) * 100}%` }}
                            >
                                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover:opacity-100 shadow-lg transform scale-0 group-hover:scale-100 transition-all" />
                            </div>
                        </div>
                        <span>{formatTime(duration)}</span>
                    </div>
                </div>

                {/* Volume & Expand/Close */}
                <div className={cn("flex items-center justify-end gap-4", isExpanded ? "absolute top-8 right-8" : "w-1/3")}>
                    <div className="flex items-center gap-2 group">
                        <button onClick={() => setVolume(volume === 0 ? 1 : 0)} className="text-gray-400 hover:text-white">
                            {volume === 0 ? <VolumeX size={20} /> : <Volume2 size={20} />}
                        </button>
                        <div
                            className="w-24 h-1 bg-white/10 rounded-full overflow-hidden cursor-pointer relative"
                            onClick={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect()
                                const x = e.clientX - rect.left
                                const newVolume = Math.max(0, Math.min(1, x / rect.width))
                                setVolume(newVolume)
                            }}
                        >
                            <div
                                className="h-full bg-white group-hover:bg-primary transition-colors absolute top-0 left-0"
                                style={{ width: `${volume * 100}%` }}
                            />
                        </div>
                    </div>
                    <button
                        onClick={() => setShowVisualizer(!showVisualizer)}
                        className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-full transition-all text-sm font-medium",
                            showVisualizer
                                ? "text-primary bg-primary/10 border border-primary/20 shadow-[0_0_10px_rgba(34,197,94,0.2)]"
                                : "text-gray-400 bg-white/5 border border-white/5 hover:bg-white/10 hover:text-white"
                        )}
                        title="Toggle Visualizer"
                    >
                        <Activity size={16} />
                        <span>Visualizer</span>
                    </button>
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="text-gray-400 hover:text-white p-2 hover:bg-white/10 rounded-full transition-colors"
                    >
                        {isExpanded ? <X size={24} /> : <Maximize2 size={20} />}
                    </button>
                </div>
            </div>

            <audio
                ref={audioRef}
                src={streamUrl}
                crossOrigin="anonymous"
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => togglePlay()}
            />
        </motion.div>
    )
}
