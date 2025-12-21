import { useState } from 'react'
import { Music } from 'lucide-react'
// import { motion } from 'framer-motion'
import Button from '../components/ui/Button'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'

interface CreatePlaylistForm {
    name: string
    description: string
}

export default function CreatePlaylist() {
    const { register, handleSubmit, formState: { errors } } = useForm<CreatePlaylistForm>()
    const [isLoading, setIsLoading] = useState(false)

    const onSubmit = async (data: CreatePlaylistForm) => {
        setIsLoading(true)
        try {
            // Mock API call
            await new Promise(resolve => setTimeout(resolve, 1000))
            toast.success(`Playlist "${data.name}" created!`)
        } catch (error) {
            toast.error('Failed to create playlist')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div className="text-center space-y-4">
                <h1 className="text-4xl font-bold tracking-tight text-white">Create Playlist</h1>
                <p className="text-gray-400">Curate your own collection of tracks.</p>
            </div>

            <div className="bg-black/20 backdrop-blur-xl rounded-3xl border border-white/5 p-8 shadow-2xl">
                <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col md:flex-row gap-8">
                    <div className="w-full md:w-64 flex-shrink-0 flex flex-col items-center gap-4">
                        <div className="w-64 h-64 bg-white/5 border-2 border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center group hover:border-primary/50 hover:bg-white/10 transition-all cursor-pointer relative overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-br from-gray-800/50 to-black/50 opacity-0 group-hover:opacity-100 transition-opacity" />
                            <Music size={48} className="text-gray-600 group-hover:text-primary transition-colors mb-2 relative z-10" />
                            <span className="text-sm font-medium text-gray-500 group-hover:text-white transition-colors relative z-10">Choose Cover</span>
                            <input type="file" className="absolute inset-0 opacity-0 cursor-pointer z-20" accept="image/*" />
                        </div>
                    </div>

                    <div className="flex-1 space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-300 ml-1">Name</label>
                            <input
                                {...register('name', { required: 'Playlist name is required' })}
                                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
                                placeholder="My Awesome Playlist"
                            />
                            {errors.name && <span className="text-red-400 text-xs ml-1">{errors.name.message}</span>}
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-300 ml-1">Description</label>
                            <textarea
                                {...register('description')}
                                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all min-h-[120px] resize-none"
                                placeholder="Give your playlist a catchy description..."
                            />
                        </div>

                        <div className="pt-4">
                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                className="w-full md:w-auto px-8"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <span className="flex items-center gap-2">
                                        <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                                        Creating...
                                    </span>
                                ) : (
                                    'Create'
                                )}
                            </Button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    )
}
