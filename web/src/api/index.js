import request from '@/utils/request'

export default {
    // Authentication APIs.
    auth: {
        login: (data) => request.post('/base/access_token', data, { noNeedToken: true, noAuthRefresh: true }),
        refreshToken: () => request.post('/base/refresh_token', undefined, { noNeedToken: true, noAuthRefresh: true }),
        getAppMeta: () => request.get('/base/app_meta', { noNeedToken: true, noAuthRefresh: true }),
        getOverview: () => request.get('/base/overview'),
        getUserInfo: () => request.get('/base/userinfo'),
        getUserMenu: () => request.get('/base/usermenu'),
        getUserApi: () => request.get('/base/userapi'),
        getPasswordPolicy: () => request.get('/base/password_policy'),
        updatePassword: (data = {}) => request.post('/base/update_password', data),
        updateProfile: (data = {}) => request.post('/base/update_profile', data),
        uploadAvatar: (file) => {
            const formData = new FormData()
            formData.append('file', file)
            return request.post('/base/upload_avatar', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
        },
        logout: () => request.post('/base/logout'),
    },

    // System settings APIs.
    systemSettings: {
        getApplicationSettings: () => request.get('/system_settings/application'),
        updateApplicationSettings: (data = {}) => request.post('/system_settings/application', data),
        getLoggingSettings: () => request.get('/system_settings/logging'),
        updateLoggingSettings: (data = {}) => request.post('/system_settings/logging', data),
        getSecuritySettings: () => request.get('/system_settings/security'),
        updateSecuritySettings: (data = {}) => request.post('/system_settings/security', data),
        getStorageSettings: () => request.get('/system_settings/storage'),
        updateStorageSettings: (data = {}) => request.post('/system_settings/storage', data),
    },

    // User management APIs.
    users: {
        getList: (params = {}) => request.get('/user/list', { params }),
        getById: (id) => request.get(`/user/get`, { params: { id } }),
        create: (data = {}) => request.post('/user/create', data),
        update: (data = {}) => request.post('/user/update', data),
        delete: (data) => request.delete(`/user/delete`, { params: data }),
        resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
    },

    // Role management APIs.
    roles: {
        getList: (params = {}) => request.get('/role/list', { params }),
        getById: (roleId) => request.get('/role/get', { params: { role_id: roleId } }),
        getPermissionOptions: () => request.get('/role/permission_options'),
        create: (data = {}) => request.post('/role/create', data),
        update: (data = {}) => request.post('/role/update', data),
        delete: (data) => request.delete('/role/delete', { params: data }),
    },

    // API management APIs.
    apis: {
        getList: (params = {}) => request.get('/api/list', { params }),
        create: (data = {}) => request.post('/api/create', data),
        update: (data = {}) => request.post('/api/update', data),
        delete: (data) => request.delete('/api/delete', { params: data }),
        refresh: () => request.post('/api/refresh'),
        getTags: () => request.get('/api/tags'),
    },
    // Audit log APIs.
    auditLogs: {
        getList: (params = {}) => request.get('/auditlog/list', { params }),
        getDetail: (id) => request.get(`/auditlog/detail/${id}`),
        delete: (id) => request.delete(`/auditlog/delete/${id}`),
        batchDelete: (data) => request.delete('/auditlog/batch_delete', { data }),
        clear: (params = {}) => request.delete('/auditlog/clear', { params }),
        export: (data = {}) => request.post('/auditlog/export', data),
        download: (filename) => request.get(`/auditlog/download/${filename}`, { responseType: 'blob' }),
        getStatistics: (params = {}) => request.get('/auditlog/statistics', { params }),
    },

    // File upload APIs.
    upload: {
        // Upload a single image.
        uploadImage: (file) => {
            const formData = new FormData()
            formData.append('file', file)
            return request.post('/upload/image', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
        },
        // Upload multiple files.
        uploadFiles: (files) => {
            const formData = new FormData()
            files.forEach(file => {
                formData.append('files', file)
            })
            return request.post('/upload/files', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
        },
        // Get the file list.
        getFiles: (params = {}) => request.get('/upload/list', { params }),
        // Delete a file.
        deleteFile: (fileKey) => request.delete('/upload/delete', { params: { file_key: fileKey } })
    },
} 
