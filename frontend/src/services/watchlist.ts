import api from './api'

export const getWatchlist = async () => {
    const response = await api.get('/watchlist/list')
    return response.data
}

export const addToWatchlist = async (data: any) => {
    const response = await api.post('/watchlist/add', data)
    return response.data
}

export const removeFromWatchlist = async (id: string) => {
    const response = await api.delete(`/watchlist/remove/${id}`)
    return response.data
}
