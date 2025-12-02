import { Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import Player from '../player/Player'

export default function Layout() {
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            setMousePosition({ x: e.clientX, y: e.clientY })
        }

        window.addEventListener('mousemove', handleMouseMove)
        return () => window.removeEventListener('mousemove', handleMouseMove)
    }, [])

    return (
        <div className="flex h-screen bg-black text-foreground overflow-hidden p-2 gap-2 relative group">
            {/* Ambient Background Effects */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/10 rounded-full blur-[150px] animate-blob" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 rounded-full blur-[150px] animate-blob animation-delay-2000" />
                <div className="absolute top-[40%] left-[40%] w-[30%] h-[30%] bg-blue-500/10 rounded-full blur-[150px] animate-blob animation-delay-4000" />
            </div>

            {/* Mouse Spotlight */}
            <div
                className="pointer-events-none fixed inset-0 z-50 transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                style={{
                    background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(255,255,255,0.06), transparent 40%)`,
                }}
            />

            <div className="w-72 h-full flex-shrink-0 z-30">
                <Sidebar />
            </div>
            <div className="flex-1 flex flex-col overflow-hidden bg-black/40 backdrop-blur-3xl rounded-xl relative border border-white/5 shadow-2xl z-10">
                <Navbar />
                <main className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar pb-24">
                    <Outlet />
                </main>
                <Player />
            </div>
        </div>
    )
}
