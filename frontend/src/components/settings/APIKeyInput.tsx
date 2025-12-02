import { Eye, EyeOff, Key } from 'lucide-react'
import { useState } from 'react'


interface APIKeyInputProps {
    label: string
    value: string
    onChange: (value: string) => void
    placeholder?: string
}

export default function APIKeyInput({ label, value, onChange, placeholder }: APIKeyInputProps) {
    const [show, setShow] = useState(false)
    const [isFocused, setIsFocused] = useState(false)

    return (
        <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300 ml-1">{label}</label>
            <div className="relative group">
                <div className={`absolute inset-0 bg-primary/20 rounded-xl blur-lg transition-opacity duration-300 ${isFocused ? 'opacity-100' : 'opacity-0'}`} />

                <Key className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-primary transition-colors" size={18} />

                <input
                    type={show ? 'text' : 'password'}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder={placeholder}
                    className="w-full pl-12 pr-12 py-3.5 rounded-xl bg-black/20 border border-white/10 text-white placeholder:text-gray-600 focus:outline-none focus:border-primary/50 focus:bg-black/40 transition-all relative z-10"
                />

                <button
                    type="button"
                    onClick={() => setShow(!show)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors z-20"
                >
                    {show ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
            </div>
        </div>
    )
}
