/**
 * 错误处理工具函数
 * 处理常见的HTTP错误码和错误消息，明确区分错误类型
 */

import { clearSession } from '@/utils/session'

// 错误类型枚举
export const ERROR_TYPES = {
    BUSINESS_ERROR: 'business_error',    // 业务逻辑错误
    NETWORK_ERROR: 'network_error',      // 网络连接错误
    AUTH_ERROR: 'auth_error',            // 认证授权错误
    SYSTEM_ERROR: 'system_error',        // 系统错误
}

// 通用错误映射
const ERROR_CODE_MAP = {
    400: '请求参数错误',
    401: '登录已过期，请重新登录',
    403: '没有权限访问',
    404: '请求的资源不存在',
    405: '请求方法不允许',
    408: '请求超时',
    422: '数据验证失败',
    429: '请求过于频繁，请稍后再试',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务暂不可用',
    504: '网关超时',
}

// 业务错误状态码 (通常这些有正常的响应结构)
const BUSINESS_ERROR_CODES = [400, 422, 409, 412]

// 认证错误状态码
const AUTH_ERROR_CODES = [401, 403]

// 系统错误状态码
const SYSTEM_ERROR_CODES = [500, 502, 503, 504]

/**
 * 标准化错误对象结构
 * @param {string} type - 错误类型
 * @param {string} message - 错误消息
 * @param {number} code - 错误代码
 * @param {Object} originalError - 原始错误对象
 * @param {any} data - 附加数据
 * @returns {Object} 标准化的错误对象
 */
export const createStandardError = (type, message, code = 0, originalError = null, data = null) => {
    return {
        type,
        message,
        code,
        data,
        originalError,
        timestamp: new Date().toISOString(),
    }
}

/**
 * 判断错误类型
 * @param {Object} error - 错误对象
 * @returns {string} 错误类型
 */
export const getErrorType = (error) => {
    // 网络错误
    if (!error.response) {
        return ERROR_TYPES.NETWORK_ERROR
    }

    const { status } = error.response

    // 认证错误
    if (AUTH_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.AUTH_ERROR
    }

    // 业务错误
    if (BUSINESS_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.BUSINESS_ERROR
    }

    // 系统错误
    if (SYSTEM_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.SYSTEM_ERROR
    }

    // 其他HTTP错误默认为业务错误
    return ERROR_TYPES.BUSINESS_ERROR
}

/**
 * 从响应中提取错误消息
 * @param {Object} response - 响应对象
 * @param {string} defaultMessage - 默认错误消息
 * @returns {string} 错误消息
 */
export const extractErrorMessage = (response, defaultMessage) => {
    if (!response || !response.data) {
        return defaultMessage
    }

    const { data, status } = response

    // 优先使用后端返回的错误消息
    if (data.msg) return data.msg
    if (data.message) return data.message
    if (data.detail) return data.detail

    // 使用通用错误映射
    return ERROR_CODE_MAP[status] || defaultMessage
}

/**
 * 处理认证错误
 * @param {number} status - HTTP状态码
 * @returns {boolean} 是否处理了认证错误
 */
export const handleAuthError = (status) => {
    if (status === 401) {
        clearSession()

        // 避免在登录页重复重定向
        if (window.location.pathname !== '/login') {
            window.location.href = '/login'
        }
        return true
    }
    return false
}

/**
 * 检查响应是否为业务成功
 * @param {Object} response - 响应对象
 * @returns {boolean} 是否为业务成功
 */
export const isBusinessSuccess = (response) => {
    // HTTP状态码200-299为成功
    if (response.status >= 200 && response.status < 300) {
        // 检查业务状态码（如果存在）
        if (response.data && typeof response.data.code !== 'undefined') {
            return response.data.code === 200 || response.data.code === 0
        }
        return true
    }
    return false
}

/**
 * 检查响应是否为业务错误
 * @param {Object} response - 响应对象
 * @returns {boolean} 是否为业务错误
 */
export const isBusinessError = (response) => {
    // HTTP状态码在业务错误范围内，或者业务状态码表示错误
    if (BUSINESS_ERROR_CODES.includes(response.status)) {
        return true
    }

    // 检查业务状态码
    if (response.data && typeof response.data.code !== 'undefined') {
        return response.data.code !== 200 && response.data.code !== 0
    }

    return false
}

/**
 * 解析错误对象
 * @param {Object} error - 原始错误对象
 * @param {string} defaultMessage - 默认错误消息
 * @returns {Object} 标准化的错误对象
 */
export const parseError = (error, defaultMessage = '操作失败，请重试') => {
    const errorType = getErrorType(error)

    switch (errorType) {
        case ERROR_TYPES.NETWORK_ERROR:
            return createStandardError(
                ERROR_TYPES.NETWORK_ERROR,
                '网络连接失败，请检查网络设置',
                0,
                error
            )

        case ERROR_TYPES.AUTH_ERROR: {
            const authMessage = extractErrorMessage(error.response, '认证失败')
            return createStandardError(
                ERROR_TYPES.AUTH_ERROR,
                authMessage,
                error.response.status,
                error
            )
        }

        case ERROR_TYPES.BUSINESS_ERROR: {
            const businessMessage = extractErrorMessage(error.response, defaultMessage)
            return createStandardError(
                ERROR_TYPES.BUSINESS_ERROR,
                businessMessage,
                error.response.status,
                error,
                error.response.data
            )
        }

        case ERROR_TYPES.SYSTEM_ERROR: {
            const systemMessage = extractErrorMessage(error.response, '系统错误，请稍后重试')
            return createStandardError(
                ERROR_TYPES.SYSTEM_ERROR,
                systemMessage,
                error.response.status,
                error
            )
        }

        default:
            return createStandardError(
                ERROR_TYPES.BUSINESS_ERROR,
                defaultMessage,
                error.response?.status || 0,
                error
            )
    }
}

/**
 * 全局错误处理器配置
 */
class GlobalErrorHandler {
    constructor() {
        this.handlers = new Map()
        this.defaultHandler = null
    }

    /**
     * 注册错误处理器
     * @param {string} errorType - 错误类型
     * @param {Function} handler - 处理函数
     */
    register(errorType, handler) {
        this.handlers.set(errorType, handler)
    }

    /**
     * 设置默认错误处理器
     * @param {Function} handler - 默认处理函数
     */
    setDefault(handler) {
        this.defaultHandler = handler
    }

    /**
     * 处理错误
     * @param {Object} error - 标准化错误对象
     * @param {Function} customHandler - 自定义处理函数
     * @returns {any} 处理结果
     */
    handle(error, customHandler = null) {
        // 优先使用自定义处理器
        if (customHandler && typeof customHandler === 'function') {
            return customHandler(error)
        }

        // 使用注册的类型处理器
        const typeHandler = this.handlers.get(error.type)
        if (typeHandler) {
            return typeHandler(error)
        }

        // 使用默认处理器
        if (this.defaultHandler) {
            return this.defaultHandler(error)
        }

        // 最后的兜底处理
        console.error('Unhandled error:', error)
        return error
    }
}

// 导出全局错误处理器实例
export const globalErrorHandler = new GlobalErrorHandler() 
