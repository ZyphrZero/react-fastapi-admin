import axios from 'axios'
import { isBusinessError, isBusinessSuccess, handleAuthError } from '@/utils/errorHandler'
import { clearSession, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from '@/utils/session'

// 创建axios实例
const request = axios.create({
    baseURL: '/api', // API基础路径
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

const refreshClient = axios.create({
    baseURL: '/api',
    timeout: 10000,
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
    const refreshToken = getRefreshToken()
    if (!refreshToken) {
        throw new Error('Missing refresh token')
    }

    const response = await refreshClient.post('/base/refresh_token', { refresh_token: refreshToken })
    if (!isBusinessSuccess(response)) {
        throw createBusinessError(response, 'Refresh token rejected')
    }

    const payload = response.data?.data
    if (!payload?.access_token || !payload?.refresh_token) {
        throw new Error('Invalid refresh token response')
    }

    setAccessToken(payload.access_token)
    setRefreshToken(payload.refresh_token)
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

// 请求拦截器
request.interceptors.request.use(
    async (config) => {
        if (config.noNeedToken) {
            return config
        }

        let token = getAccessToken()
        if (!token && getRefreshToken()) {
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

// 响应拦截器
request.interceptors.response.use(
    (response) => {
        // 如果是文件下载等特殊响应，直接返回
        if (response.config.responseType === 'blob') {
            return response
        }

        // 检查是否为业务成功
        if (isBusinessSuccess(response)) {
            return response.data
        }

        // 检查是否为业务错误（在正常HTTP响应中）
        if (isBusinessError(response)) {
            // 处理认证错误
            if (response.status === 401) {
                handleAuthError(response.status)
            }

            // 创建业务错误对象并抛出
            const error = new Error('Business Error')
            error.response = response
            return Promise.reject(error)
        }

        // 其他情况直接返回数据
        return response.data
    },
    async (error) => {
        // 处理网络错误和HTTP错误状态码
        const originalRequest = error.config || {}

        if (
            error.response?.status === 401 &&
            !originalRequest.noNeedToken &&
            !originalRequest.noAuthRefresh &&
            !originalRequest._retry &&
            getRefreshToken()
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

        // 拒绝Promise，让组件处理具体的错误显示
        return Promise.reject(error)
    }
)

export default request 
