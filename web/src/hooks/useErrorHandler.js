import { useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { parseError, globalErrorHandler, ERROR_TYPES } from '@/utils/errorHandler'

const MESSAGE_DEDUPE_WINDOW_MS = 2000
const messageShownAt = new Map()

/**
 * 错误处理Hook
 * 基于 sonner 封装统一消息提示与错误处理
 * 支持自定义错误处理器和全局错误处理
 */
export const useErrorHandler = () => {
    const message = useMemo(() => ({
        open: ({ type = 'info', content, key, duration }) => toast[type]?.(content, { id: key, duration }),
        success: (content, options = {}) => toast.success(content, options),
        warning: (content, options = {}) => toast.warning(content, options),
        info: (content, options = {}) => toast.info(content, options),
        error: (content, options = {}) => toast.error(content, options),
        loading: (content, duration = Infinity) => toast.loading(content, { duration }),
    }), [])

    const showDedupedMessage = useCallback((type, content, options = {}) => {
        if (!content) return

        const now = Date.now()
        const dedupeKey = options.key || `${type}:${content}`
        const dedupeWindow = options.dedupeWindow ?? MESSAGE_DEDUPE_WINDOW_MS
        const lastShownAt = messageShownAt.get(dedupeKey) ?? 0

        if (now - lastShownAt < dedupeWindow) {
            return
        }

        messageShownAt.set(dedupeKey, now)

        message.open({
            type,
            content,
            key: dedupeKey,
            duration: options.duration,
        })
    }, [message])

    /**
     * 默认错误处理逻辑
     * @param {Object} standardError - 标准化错误对象
     */
    const handleDefaultError = useCallback((standardError) => {
        const errorKey = `error:${standardError.code}:${standardError.message}`

        switch (standardError.type) {
            case ERROR_TYPES.BUSINESS_ERROR:
                showDedupedMessage('error', standardError.message, { key: errorKey })
                break
            case ERROR_TYPES.NETWORK_ERROR:
                showDedupedMessage('error', standardError.message, { key: errorKey })
                break
            case ERROR_TYPES.AUTH_ERROR:
                showDedupedMessage('error', standardError.message, { key: errorKey })
                break
            case ERROR_TYPES.SYSTEM_ERROR:
                showDedupedMessage('error', standardError.message, { key: errorKey })
                break
            default:
                showDedupedMessage('error', standardError.message, { key: errorKey })
        }
    }, [showDedupedMessage])

    /**
     * 处理API错误的通用方法
     * @param {Object} error - 原始错误对象
     * @param {string} defaultMessage - 默认错误消息
     * @param {Function} customHandler - 自定义错误处理函数
     * @returns {Object} 标准化的错误对象
     */
    const handleError = useCallback((error, defaultMessage = '操作失败，请重试', customHandler = null) => {
        // 解析错误对象
        const standardError = parseError(error, defaultMessage)

        // 如果有自定义处理器，使用自定义处理器
        if (customHandler && typeof customHandler === 'function') {
            return customHandler(standardError)
        }

        // 使用全局错误处理器
        const result = globalErrorHandler.handle(standardError)

        // 如果全局处理器没有处理，使用默认处理逻辑
        if (result === standardError) {
            handleDefaultError(standardError)
        }

        return standardError
    }, [handleDefaultError])

    /**
     * 处理业务错误（始终显示错误消息）
     * @param {Object} error - 错误对象
     * @param {string} defaultMessage - 默认错误消息
     * @param {Function} customHandler - 自定义错误处理函数
     * @returns {Object} 标准化的错误对象
     */
    const handleBusinessError = useCallback((error, defaultMessage = '操作失败，请重试', customHandler = null) => {
        const standardError = parseError(error, defaultMessage)

        if (customHandler && typeof customHandler === 'function') {
            return customHandler(standardError)
        }

        showDedupedMessage('error', standardError.message, {
            key: `error:${standardError.code}:${standardError.message}`,
        })
        return standardError
    }, [showDedupedMessage])

    /**
     * 静默处理错误（不显示消息）
     * @param {Object} error - 错误对象
     * @param {string} defaultMessage - 默认错误消息
     * @returns {Object} 标准化的错误对象
     */
    const handleSilentError = useCallback((error, defaultMessage = '操作失败，请重试') => {
        return parseError(error, defaultMessage)
    }, [])

    /**
     * 处理网络错误
     * @param {Object} error - 错误对象
     * @param {Function} customHandler - 自定义错误处理函数
     * @returns {Object} 标准化的错误对象
     */
    const handleNetworkError = useCallback((error, customHandler = null) => {
        const standardError = parseError(error, '网络连接失败，请检查网络设置')

        if (customHandler && typeof customHandler === 'function') {
            return customHandler(standardError)
        }

        if (standardError.type === ERROR_TYPES.NETWORK_ERROR) {
            showDedupedMessage('error', standardError.message, {
                key: `error:${standardError.code}:${standardError.message}`,
            })
        }

        return standardError
    }, [showDedupedMessage])

    /**
     * 注册全局错误处理器
     * @param {string} errorType - 错误类型
     * @param {Function} handler - 处理函数
     */
    const registerGlobalHandler = useCallback((errorType, handler) => {
        globalErrorHandler.register(errorType, handler)
    }, [])

    /**
     * 设置默认全局错误处理器
     * @param {Function} handler - 默认处理函数
     */
    const setDefaultGlobalHandler = useCallback((handler) => {
        globalErrorHandler.setDefault(handler)
    }, [])

    /**
     * 显示成功消息
     * @param {string} msg - 成功消息
     */
    const showSuccess = useCallback((msg) => {
        message.success(msg)
    }, [message])

    /**
     * 显示警告消息
     * @param {string} msg - 警告消息
     */
    const showWarning = useCallback((msg) => {
        message.warning(msg)
    }, [message])

    /**
     * 显示信息消息
     * @param {string} msg - 信息消息
     */
    const showInfo = useCallback((msg) => {
        message.info(msg)
    }, [message])

    /**
     * 显示加载消息
     * @param {string} msg - 加载消息
     * @param {number} duration - 持续时间
     */
    const showLoading = useCallback((msg = '加载中...', duration = 0) => {
        return message.loading(msg, duration)
    }, [message])

    return useMemo(() => ({
        // 错误处理方法
        handleError,
        handleBusinessError,
        handleSilentError,
        handleNetworkError,

        // 全局错误处理器管理
        registerGlobalHandler,
        setDefaultGlobalHandler,

        // 消息显示方法
        showSuccess,
        showWarning,
        showInfo,
        showLoading,

        // 原始API（备用）
        message,
    }), [
        handleBusinessError,
        handleError,
        handleNetworkError,
        handleSilentError,
        message,
        registerGlobalHandler,
        setDefaultGlobalHandler,
        showInfo,
        showLoading,
        showSuccess,
        showWarning,
    ])
}
