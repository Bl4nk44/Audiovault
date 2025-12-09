import { Github } from 'lucide-react'
import { useTranslation } from '../../hooks/useTranslation'

export default function Footer() {
    const { t } = useTranslation()
    
    return (
        <footer className="mt-12 pb-8 text-center text-sm text-muted-foreground border-t border-white/5 pt-8">
            <div className="flex items-center justify-center gap-4">
                <p>Audiovault v{__APP_VERSION__}</p>
                <span className="text-white/10">|</span>
                <a
                    href="https://github.com/Bl4nk44/Audiovault"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 hover:text-primary transition-colors"
                >
                    <Github size={14} />
                    GitHub
                </a>
            </div>
            <p className="text-sm text-base-content/60">
                © {new Date().getFullYear()} Audiovault. {t('footer.rights')}
            </p>
        </footer>
    )
}
