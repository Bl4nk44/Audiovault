import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useStore } from '../../store/useStore'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import { User, Lock, Save, Camera } from 'lucide-react'
import Button from '../ui/Button'

export default function AccountSettings() {
    const { user, setUser } = useStore()
    const [isLoading, setIsLoading] = useState(false)
    const { register, handleSubmit, formState: { errors } } = useForm({
        defaultValues: {
            username: user?.username || '',
            avatar_url: user?.preferences?.avatar_url || ''
        }
    })

    const { register: registerPassword, handleSubmit: handleSubmitPassword, reset: resetPassword, formState: { errors: passwordErrors } } = useForm()

    const onUpdateProfile = async (data: any) => {
        setIsLoading(true)
        try {
            const response = await api.put('/users/me', data)
            setUser({ ...user!, ...response.data.user })
            toast.success('Profile updated successfully')
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update profile')
        } finally {
            setIsLoading(false)
        }
    }

    const onUpdatePassword = async (data: any) => {
        setIsLoading(true)
        try {
            await api.put('/users/me/password', {
                current_password: data.currentPassword,
                new_password: data.newPassword
            })
            toast.success('Password updated successfully')
            resetPassword()
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update password')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="space-y-8">
            {/* Profile Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl"
            >
                <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6 flex items-center gap-3">
                    <User className="text-primary" size={24} />
                    Profile Information
                </h3>

                <form onSubmit={handleSubmit(onUpdateProfile)} className="space-y-6">
                    <div className="flex items-center gap-6 mb-8">
                        <div className="relative group">
                            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-green-600 flex items-center justify-center shadow-lg overflow-hidden">
                                {user?.preferences?.avatar_url ? (
                                    <img src={user.preferences.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                                ) : (
                                    <User size={40} className="text-black" />
                                )}
                            </div>
                            <button type="button" className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                                <Camera className="text-white" size={24} />
                            </button>
                        </div>
                        <div>
                            <h4 className="text-lg font-bold text-white">{user?.username}</h4>
                            <p className="text-gray-400 text-sm">{user?.email}</p>
                        </div>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-300 ml-1">Username</label>
                            <input
                                {...register('username', { required: 'Username is required' })}
                                className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                            />
                            {errors.username && <span className="text-red-400 text-xs ml-1">{errors.username.message as string}</span>}
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-300 ml-1">Avatar URL</label>
                            <input
                                {...register('avatar_url')}
                                placeholder="https://example.com/avatar.jpg"
                                className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button type="submit" isLoading={isLoading} variant="primary" className="px-6">
                            <Save size={18} className="mr-2" /> Save Profile
                        </Button>
                    </div>
                </form>
            </motion.div>

            {/* Password Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl"
            >
                <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6 flex items-center gap-3">
                    <Lock className="text-red-500" size={24} />
                    Change Password
                </h3>

                <form onSubmit={handleSubmitPassword(onUpdatePassword)} className="space-y-6 max-w-md">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1">Current Password</label>
                        <input
                            type="password"
                            {...registerPassword('currentPassword', { required: 'Current password is required' })}
                            className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                        />
                        {passwordErrors.currentPassword && <span className="text-red-400 text-xs ml-1">{passwordErrors.currentPassword.message as string}</span>}
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1">New Password</label>
                        <input
                            type="password"
                            {...registerPassword('newPassword', {
                                required: 'New password is required',
                                minLength: { value: 6, message: 'Minimum 6 characters' }
                            })}
                            className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                        />
                        {passwordErrors.newPassword && <span className="text-red-400 text-xs ml-1">{passwordErrors.newPassword.message as string}</span>}
                    </div>

                    <div className="flex justify-end">
                        <Button type="submit" isLoading={isLoading} variant="outline" className="px-6 hover:bg-red-500/10 hover:text-red-500 hover:border-red-500/50">
                            Update Password
                        </Button>
                    </div>
                </form>
            </motion.div>
        </div>
    )
}
