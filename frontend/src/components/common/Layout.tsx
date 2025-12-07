import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import Player from '../player/Player'

import Footer from './Footer'

export default function Layout() {
    return (
        <div className="flex h-screen bg-black text-foreground overflow-hidden p-2 gap-2 relative group">
            <div className="w-72 h-full flex-shrink-0 z-30">
                <Sidebar />
            </div>
            <div className="flex-1 flex flex-col overflow-hidden bg-black/40 backdrop-blur-3xl rounded-xl relative border border-white/5 shadow-2xl z-10">
                <Navbar />
                <main className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar pb-24">
                    <Outlet />
                    <Footer />
                </main>
                <Player />
            </div>
        </div>
    )
}
