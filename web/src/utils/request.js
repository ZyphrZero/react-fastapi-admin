import axios from 'axios'
import { isBusinessError, isBusinessSuccess, handleAuthError } from '@/utils/errorHandler'
import { getAccessToken } from '@/utils/session'

// 创建axios实例
const request = axios.create({
    baseURL: '/api', // API基础路径
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// 请求拦截器
request.interceptors.request.use(
    (config) => {
        const token = getAccessToken()
        if (token && !config.noNeedToken) {
            config.headers.token = token
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
    (error) => {
        // 处理网络错误和HTTP错误状态码

        // 处理认证错误
        if (error.response?.status === 401) {
            handleAuthError(error.response.status)
        }

        // 拒绝Promise，让组件处理具体的错误显示
        return Promise.reject(error)
    }
)

export default request 
