import axios from 'axios'
import { useStore } from '../store/useStore'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

api.interceptors.request.use((config) => {
    const token = useStore.getState().token
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useStore.getState().logout()
        }
        return Promise.reject(error)
    }
)

export default api
