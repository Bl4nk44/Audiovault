import { Github } from 'lucide-react'
import { useTranslation } from '../../hooks/useTranslation'

export default function Footer() {
    // We can use translation if we want, but "Spotizerr" and "GitHub" are universal.
    // Maybe "Version"?
    return (
        <footer className="mt-12 pb-8 text-center text-sm text-muted-foreground border-t border-white/5 pt-8">
            <div className="flex items-center justify-center gap-4">
                <p>Spotizerr v1.0.0</p>
                <span className="text-white/10">|</span>
                <a
                    href="https://github.com/Bl4nk44/SpotizerrNew"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 hover:text-primary transition-colors"
                >
                    <Github size={14} />
                    GitHub
                </a>
            </div>
            <div className="mt-2 text-xs text-white/20">
                Created with ❤️ by Antigravity
            </div>
        </footer>
    )
}
