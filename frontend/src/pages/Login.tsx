import LoginForm from '../components/auth/LoginForm'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

export default function Login() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background text-foreground relative overflow-hidden">

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
                        Welcome Back
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-muted-foreground mt-2"
                    >
                        Sign in to continue to Spotizerr
                    </motion.p>
                </div>

                <LoginForm />

                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="mt-8 text-center text-sm text-muted-foreground"
                >
                    Don't have an account?{' '}
                    <Link to="/register" className="text-primary hover:text-green-400 font-medium hover:underline transition-all">
                        Create account
                    </Link>
                </motion.p>
            </motion.div>
        </div>
    )
}
