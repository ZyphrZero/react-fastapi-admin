import { useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { parseError, globalErrorHandler, ERROR_TYPES } from '@/utils/errorHandler'

const MESSAGE_DEDUPE_WINDOW_MS = 2000
const messageShownAt = new Map()

/**
 * Error-handling hook.
 * Wraps sonner with unified notifications and error handling.
 * Supports custom error handlers and a global error handler.
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
     * Default error-handling logic.
     * @param {Object} standardError - Standardized error object.
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
     * Generic helper for API errors.
     * @param {Object} error - Original error object.
     * @param {string} defaultMessage - Default error message.
     * @param {Function} customHandler - Custom error handler.
     * @returns {Object} Standardized error object.
     */
    const handleError = useCallback((error, defaultMessage = '操作失败，请重试', customHandler = null) => {
        // Parse the error object.
        const standardError = parseError(error, defaultMessage)

        // Use the custom handler when one is provided.
        if (customHandler && typeof customHandler === 'function') {
            return customHandler(standardError)
        }

        // Use the global error handler.
        const result = globalErrorHandler.handle(standardError)

        // Fall back to the default handler when the global handler does not consume the error.
        if (result === standardError) {
            handleDefaultError(standardError)
        }

        return standardError
    }, [handleDefaultError])

    /**
     * Handle business errors and always show a message.
     * @param {Object} error - Error object.
     * @param {string} defaultMessage - Default error message.
     * @param {Function} customHandler - Custom error handler.
     * @returns {Object} Standardized error object.
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
     * Handle errors silently without showing a message.
     * @param {Object} error - Error object.
     * @param {string} defaultMessage - Default error message.
     * @returns {Object} Standardized error object.
     */
    const handleSilentError = useCallback((error, defaultMessage = '操作失败，请重试') => {
        return parseError(error, defaultMessage)
    }, [])

    /**
     * Handle network errors.
     * @param {Object} error - Error object.
     * @param {Function} customHandler - Custom error handler.
     * @returns {Object} Standardized error object.
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
     * Register a global error handler.
     * @param {string} errorType - Error type.
     * @param {Function} handler - Handler function.
     */
    const registerGlobalHandler = useCallback((errorType, handler) => {
        globalErrorHandler.register(errorType, handler)
    }, [])

    /**
     * Set the default global error handler.
     * @param {Function} handler - Default handler.
     */
    const setDefaultGlobalHandler = useCallback((handler) => {
        globalErrorHandler.setDefault(handler)
    }, [])

    /**
     * Show a success message.
     * @param {string} msg - Success message.
     */
    const showSuccess = useCallback((msg) => {
        message.success(msg)
    }, [message])

    /**
     * Show a warning message.
     * @param {string} msg - Warning message.
     */
    const showWarning = useCallback((msg) => {
        message.warning(msg)
    }, [message])

    /**
     * Show an informational message.
     * @param {string} msg - Informational message.
     */
    const showInfo = useCallback((msg) => {
        message.info(msg)
    }, [message])

    /**
     * Show a loading message.
     * @param {string} msg - Loading message.
     * @param {number} duration - Duration.
     */
    const showLoading = useCallback((msg = '加载中...', duration = 0) => {
        return message.loading(msg, duration)
    }, [message])

    return useMemo(() => ({
        // Error-handling methods.
        handleError,
        handleBusinessError,
        handleSilentError,
        handleNetworkError,

        // Global error-handler management.
        registerGlobalHandler,
        setDefaultGlobalHandler,

        // Message display helpers.
        showSuccess,
        showWarning,
        showInfo,
        showLoading,

        // Raw API access (fallback).
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
