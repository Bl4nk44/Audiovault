import LoginForm from '../components/auth/LoginForm'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
export default function Login() {
    return (
        <div className="min-h-screen w-full flex items-center justify-center p-4 bg-background">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-md p-8 glass rounded-[var(--radius)]"
            >
                <div className="text-center mb-8">
                    <motion.h1
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400"
                    >
                        Login to Audiovault
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-muted-foreground mt-2"
                    >
                        Sign in to continue to Audiovault
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
