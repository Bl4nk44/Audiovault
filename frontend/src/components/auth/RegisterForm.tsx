import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { register as registerUser } from '../../services/auth'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import Button from '../ui/Button'
import { Mail, Lock, AlertCircle, User } from 'lucide-react'

export default function RegisterForm() {
    const { register, handleSubmit, watch, formState: { errors } } = useForm()
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()

    const onSubmit = async (data: any) => {
        setIsLoading(true)
        try {
            await registerUser({
                email: data.email,
                username: data.username,
                password: data.password
            })
            toast.success('Registration successful! Please login.')
            navigate('/login')
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Registration failed')
        } finally {
            setIsLoading(false)
        }
    }

    const inputVariants = {
        focus: { scale: 1.02, borderColor: "rgba(34, 197, 94, 0.5)", boxShadow: "0 0 15px rgba(34, 197, 94, 0.2)" },
        blur: { scale: 1, borderColor: "rgba(255, 255, 255, 0.1)", boxShadow: "none" }
    }

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 w-full max-w-md relative z-10">
            <div className="space-y-2">
                <label className="text-sm font-medium ml-1 text-gray-300">Username</label>
                <div className="relative group">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <motion.input
                        variants={inputVariants}
                        whileFocus="focus"
                        initial="blur"
                        {...register('username', {
                            required: 'Username is required',
                            minLength: {
                                value: 3,
                                message: "Username must be at least 3 characters"
                            }
                        })}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
                        type="text"
                        placeholder="johndoe"
                    />
                </div>
                {errors.username && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-2 text-red-400 text-xs ml-1"
                    >
                        <AlertCircle size={12} />
                        <span>{errors.username.message as string}</span>
                    </motion.div>
                )}
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium ml-1 text-gray-300">Email</label>
                <div className="relative group">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <motion.input
                        variants={inputVariants}
                        whileFocus="focus"
                        initial="blur"
                        {...register('email', {
                            required: 'Email is required',
                            pattern: {
                                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                                message: "Invalid email address"
                            }
                        })}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
                        type="email"
                        placeholder="name@example.com"
                    />
                </div>
                {errors.email && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-2 text-red-400 text-xs ml-1"
                    >
                        <AlertCircle size={12} />
                        <span>{errors.email.message as string}</span>
                    </motion.div>
                )}
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium ml-1 text-gray-300">Password</label>
                <div className="relative group">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <motion.input
                        variants={inputVariants}
                        whileFocus="focus"
                        initial="blur"
                        {...register('password', {
                            required: 'Password is required',
                            minLength: {
                                value: 6,
                                message: "Password must be at least 6 characters"
                            }
                        })}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
                        type="password"
                        placeholder="••••••••"
                    />
                </div>
                {errors.password && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-2 text-red-400 text-xs ml-1"
                    >
                        <AlertCircle size={12} />
                        <span>{errors.password.message as string}</span>
                    </motion.div>
                )}
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium ml-1 text-gray-300">Confirm Password</label>
                <div className="relative group">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
                    <motion.input
                        variants={inputVariants}
                        whileFocus="focus"
                        initial="blur"
                        {...register('confirmPassword', {
                            required: 'Please confirm your password',
                            validate: (val: string) => {
                                if (watch('password') != val) {
                                    return "Your passwords do not match";
                                }
                            }
                        })}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
                        type="password"
                        placeholder="••••••••"
                    />
                </div>
                {errors.confirmPassword && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-2 text-red-400 text-xs ml-1"
                    >
                        <AlertCircle size={12} />
                        <span>{errors.confirmPassword.message as string}</span>
                    </motion.div>
                )}
            </div>

            <Button
                type="submit"
                isLoading={isLoading}
                className="w-full py-6 text-lg shadow-lg shadow-primary/20"
                variant="primary"
            >
                Create Account
            </Button>
        </form>
    )
}
