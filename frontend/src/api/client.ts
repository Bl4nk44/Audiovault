import axios from 'axios';

const apiClient = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle global errors if needed (e.g. 401 logout)
        return Promise.reject(error);
    }
);

export default apiClient;
