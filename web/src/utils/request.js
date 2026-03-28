import axios from 'axios'
import { isBusinessError, isBusinessSuccess, handleAuthError } from '@/utils/errorHandler'
import { clearSession, getAccessToken, hasRefreshSession, markRefreshSession, setAccessToken } from '@/utils/session'

// Create the Axios client.
const request = axios.create({
    baseURL: '/api', // Base API path.
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

const refreshClient = axios.create({
    baseURL: '/api',
    timeout: 10000,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
})

let refreshPromise = null

const createBusinessError = (response, message) => {
    const error = new Error(message)
    error.response = response
    return error
}

const refreshAccessToken = async () => {
    if (!hasRefreshSession()) {
        throw new Error('Missing refresh token')
    }

    const response = await refreshClient.post('/base/refresh_token')
    if (!isBusinessSuccess(response)) {
        throw createBusinessError(response, 'Refresh token rejected')
    }

    const payload = response.data?.data
    if (!payload?.access_token) {
        throw new Error('Invalid refresh token response')
    }

    setAccessToken(payload.access_token)
    markRefreshSession(true)
    return payload.access_token
}

const getRefreshPromise = () => {
    if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
        })
    }

    return refreshPromise
}

// Request interceptor.
request.interceptors.request.use(
    async (config) => {
        if (config.noNeedToken) {
            return config
        }

        let token = getAccessToken()
        if (!token && hasRefreshSession()) {
            try {
                token = await getRefreshPromise()
            } catch (error) {
                clearSession()
                handleAuthError(401)
                return Promise.reject(error)
            }
        }

        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor.
request.interceptors.response.use(
    (response) => {
        // Return special responses such as file downloads directly.
        if (response.config.responseType === 'blob') {
            return response
        }

        // Check whether the business request succeeded.
        if (isBusinessSuccess(response)) {
            return response.data
        }

        // Check whether this is a business error inside an otherwise normal HTTP response.
        if (isBusinessError(response)) {
            // Handle authentication errors.
            if (response.status === 401) {
                handleAuthError(response.status)
            }

            // Create and throw a business error object.
            const error = new Error('Business Error')
            error.response = response
            return Promise.reject(error)
        }

        // Return the payload directly for all other cases.
        return response.data
    },
    async (error) => {
        // Handle network errors and HTTP error status codes.
        const originalRequest = error.config || {}

        if (
            error.response?.status === 401 &&
            !originalRequest.noNeedToken &&
            !originalRequest.noAuthRefresh &&
            !originalRequest._retry &&
            hasRefreshSession()
        ) {
            originalRequest._retry = true
            try {
                const token = await getRefreshPromise()
                originalRequest.headers = originalRequest.headers || {}
                originalRequest.headers.Authorization = `Bearer ${token}`
                return request(originalRequest)
            } catch (refreshError) {
                clearSession()
                handleAuthError(401)
                return Promise.reject(refreshError)
            }
        }

        if (error.response?.status === 401) {
            handleAuthError(error.response.status)
        }

        // Reject the promise so components can decide how to display the error.
        return Promise.reject(error)
    }
)

export default request 
