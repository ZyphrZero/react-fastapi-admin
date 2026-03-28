/**
 * Error-handling utilities.
 * Handles common HTTP status codes and error messages while distinguishing error types explicitly.
 */

import { clearSession } from '@/utils/session'

// Error type enumeration.
export const ERROR_TYPES = {
    BUSINESS_ERROR: 'business_error',    // Business-logic error.
    NETWORK_ERROR: 'network_error',      // Network connectivity error.
    AUTH_ERROR: 'auth_error',            // Authentication or authorization error.
    SYSTEM_ERROR: 'system_error',        // System-level error.
}

// Common error mapping.
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

// Business error status codes. These usually keep a normal response shape.
const BUSINESS_ERROR_CODES = [400, 422, 409, 412]

// Authentication error status codes.
const AUTH_ERROR_CODES = [401, 403]

// System error status codes.
const SYSTEM_ERROR_CODES = [500, 502, 503, 504]

/**
 * Standardized error object shape.
 * @param {string} type - Error type.
 * @param {string} message - Error message.
 * @param {number} code - Error code.
 * @param {Object} originalError - Original error object.
 * @param {any} data - Additional data.
 * @returns {Object} Standardized error object.
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
 * Resolve the error type.
 * @param {Object} error - Error object.
 * @returns {string} Error type.
 */
export const getErrorType = (error) => {
    // Network error.
    if (!error.response) {
        return ERROR_TYPES.NETWORK_ERROR
    }

    const { status } = error.response

    // Authentication error.
    if (AUTH_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.AUTH_ERROR
    }

    // Business error.
    if (BUSINESS_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.BUSINESS_ERROR
    }

    // System error.
    if (SYSTEM_ERROR_CODES.includes(status)) {
        return ERROR_TYPES.SYSTEM_ERROR
    }

    // Treat other HTTP errors as business errors by default.
    return ERROR_TYPES.BUSINESS_ERROR
}

/**
 * Extract the error message from a response.
 * @param {Object} response - Response object.
 * @param {string} defaultMessage - Default error message.
 * @returns {string} Error message.
 */
export const extractErrorMessage = (response, defaultMessage) => {
    if (!response || !response.data) {
        return defaultMessage
    }

    const { data, status } = response

    // Prefer error messages returned by the backend.
    if (data.msg) return data.msg
    if (data.message) return data.message
    if (data.detail) return data.detail

    // Fall back to the common error mapping.
    return ERROR_CODE_MAP[status] || defaultMessage
}

/**
 * Handle authentication errors.
 * @param {number} status - HTTP status code.
 * @returns {boolean} Whether the auth error was handled.
 */
export const handleAuthError = (status) => {
    if (status === 401) {
        clearSession()

        // Avoid redirecting repeatedly on the login page.
        if (window.location.pathname !== '/login') {
            window.location.href = '/login'
        }
        return true
    }
    return false
}

/**
 * Check whether the response represents business success.
 * @param {Object} response - Response object.
 * @returns {boolean} Whether the response represents business success.
 */
export const isBusinessSuccess = (response) => {
    // HTTP 200-299 is considered successful.
    if (response.status >= 200 && response.status < 300) {
        // Check the business status code when it exists.
        if (response.data && typeof response.data.code !== 'undefined') {
            return response.data.code === 200 || response.data.code === 0
        }
        return true
    }
    return false
}

/**
 * Check whether the response represents a business error.
 * @param {Object} response - Response object.
 * @returns {boolean} Whether the response represents a business error.
 */
export const isBusinessError = (response) => {
    // Business errors can come from HTTP status codes or from business status codes in the payload.
    if (BUSINESS_ERROR_CODES.includes(response.status)) {
        return true
    }

    // Check the business status code.
    if (response.data && typeof response.data.code !== 'undefined') {
        return response.data.code !== 200 && response.data.code !== 0
    }

    return false
}

/**
 * Parse an error object.
 * @param {Object} error - Original error object.
 * @param {string} defaultMessage - Default error message.
 * @returns {Object} Standardized error object.
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
 * Global error-handler configuration.
 */
class GlobalErrorHandler {
    constructor() {
        this.handlers = new Map()
        this.defaultHandler = null
    }

    /**
     * Register an error handler.
     * @param {string} errorType - Error type.
     * @param {Function} handler - Handler function.
     */
    register(errorType, handler) {
        this.handlers.set(errorType, handler)
    }

    /**
     * Set the default error handler.
     * @param {Function} handler - Default handler.
     */
    setDefault(handler) {
        this.defaultHandler = handler
    }

    /**
     * Handle an error.
     * @param {Object} error - Standardized error object.
     * @param {Function} customHandler - Custom handler function.
     * @returns {any} Handler result.
     */
    handle(error, customHandler = null) {
        // Prefer a custom handler when provided.
        if (customHandler && typeof customHandler === 'function') {
            return customHandler(error)
        }

        // Use a registered type-specific handler.
        const typeHandler = this.handlers.get(error.type)
        if (typeHandler) {
            return typeHandler(error)
        }

        // Fall back to the default handler.
        if (this.defaultHandler) {
            return this.defaultHandler(error)
        }

        // Final fallback behavior.
        console.error('Unhandled error:', error)
        return error
    }
}

// Export the global error-handler instance.
export const globalErrorHandler = new GlobalErrorHandler() 
