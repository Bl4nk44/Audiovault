import RegisterForm from '../components/auth/RegisterForm'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

export default function Register() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background text-foreground relative overflow-hidden">
            {/* Ambient Background Effects */}
            <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/10 rounded-full blur-[150px] animate-blob" />
            <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-purple-500/10 rounded-full blur-[150px] animate-blob animation-delay-2000" />

            <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="w-full max-w-md p-8 rounded-3xl border border-white/10 bg-black/40 backdrop-blur-xl shadow-2xl relative z-10 mx-4"
            >
                <div className="text-center mb-8">
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.1 }}
                        className="w-16 h-16 bg-gradient-to-br from-primary to-green-600 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-[0_0_25px_rgba(34,197,94,0.4)]"
                    >
                        <span className="text-3xl font-bold text-black">S</span>
                    </motion.div>
                    <motion.h1
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400"
                    >
                        Join Spotizerr
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-muted-foreground mt-2"
                    >
                        Create an account to start downloading
                    </motion.p>
                </div>

                <RegisterForm />

                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="mt-8 text-center text-sm text-muted-foreground"
                >
                    Already have an account?{' '}
                    <Link to="/login" className="text-primary hover:text-green-400 font-medium hover:underline transition-all">
                        Sign in
                    </Link>
                </motion.p>
            </motion.div>
        </div>
    )
}
