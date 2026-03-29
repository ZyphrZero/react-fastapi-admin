package apis

type routeDefinition struct {
	Method  string
	Path    string
	Summary string
	Tags    string
}

func staticRouteDefinitions() []routeDefinition {
	return []routeDefinition{
		{Method: "POST", Path: "/api/v1/base/access_token", Summary: "获取token", Tags: "基础模块"},
		{Method: "POST", Path: "/api/v1/base/refresh_token", Summary: "刷新访问令牌", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/base/userinfo", Summary: "查看用户信息", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/base/usermenu", Summary: "查看用户菜单", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/base/userapi", Summary: "查看用户API", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/base/overview", Summary: "查看管理台概览", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/base/password_policy", Summary: "查看密码策略", Tags: "基础模块"},
		{Method: "POST", Path: "/api/v1/base/update_password", Summary: "修改密码", Tags: "基础模块"},
		{Method: "POST", Path: "/api/v1/base/update_profile", Summary: "更新个人信息", Tags: "基础模块"},
		{Method: "POST", Path: "/api/v1/base/upload_avatar", Summary: "上传头像", Tags: "基础模块"},
		{Method: "POST", Path: "/api/v1/base/logout", Summary: "用户注销", Tags: "基础模块"},
		{Method: "GET", Path: "/api/v1/user/list", Summary: "查看用户列表", Tags: "用户管理"},
		{Method: "GET", Path: "/api/v1/user/get", Summary: "查看用户", Tags: "用户管理"},
		{Method: "POST", Path: "/api/v1/user/create", Summary: "创建用户", Tags: "用户管理"},
		{Method: "POST", Path: "/api/v1/user/update", Summary: "更新用户", Tags: "用户管理"},
		{Method: "DELETE", Path: "/api/v1/user/delete", Summary: "删除用户", Tags: "用户管理"},
		{Method: "POST", Path: "/api/v1/user/reset_password", Summary: "重置密码", Tags: "用户管理"},
		{Method: "GET", Path: "/api/v1/role/list", Summary: "查看角色列表", Tags: "角色管理"},
		{Method: "GET", Path: "/api/v1/role/get", Summary: "查看角色", Tags: "角色管理"},
		{Method: "GET", Path: "/api/v1/role/permission_options", Summary: "获取角色权限选项", Tags: "角色管理"},
		{Method: "POST", Path: "/api/v1/role/create", Summary: "创建角色", Tags: "角色管理"},
		{Method: "POST", Path: "/api/v1/role/update", Summary: "更新角色", Tags: "角色管理"},
		{Method: "DELETE", Path: "/api/v1/role/delete", Summary: "删除角色", Tags: "角色管理"},
		{Method: "GET", Path: "/api/v1/api/list", Summary: "查看API列表", Tags: "API管理"},
		{Method: "GET", Path: "/api/v1/api/get", Summary: "查看Api", Tags: "API管理"},
		{Method: "POST", Path: "/api/v1/api/update", Summary: "更新Api", Tags: "API管理"},
		{Method: "DELETE", Path: "/api/v1/api/delete", Summary: "删除Api", Tags: "API管理"},
		{Method: "POST", Path: "/api/v1/api/refresh", Summary: "刷新API列表", Tags: "API管理"},
		{Method: "GET", Path: "/api/v1/api/tags", Summary: "获取所有API标签", Tags: "API管理"},
		{Method: "GET", Path: "/api/v1/auditlog/list", Summary: "查看操作日志", Tags: "审计日志"},
		{Method: "GET", Path: "/api/v1/auditlog/detail/{log_id}", Summary: "查看操作日志详情", Tags: "审计日志"},
		{Method: "DELETE", Path: "/api/v1/auditlog/delete/{log_id}", Summary: "删除操作日志", Tags: "审计日志"},
		{Method: "DELETE", Path: "/api/v1/auditlog/batch_delete", Summary: "批量删除操作日志", Tags: "审计日志"},
		{Method: "DELETE", Path: "/api/v1/auditlog/clear", Summary: "清空操作日志", Tags: "审计日志"},
		{Method: "POST", Path: "/api/v1/auditlog/export", Summary: "导出操作日志", Tags: "审计日志"},
		{Method: "GET", Path: "/api/v1/auditlog/download/{filename}", Summary: "下载导出的日志文件", Tags: "审计日志"},
		{Method: "GET", Path: "/api/v1/auditlog/statistics", Summary: "获取操作日志统计信息", Tags: "审计日志"},
		{Method: "POST", Path: "/api/v1/upload/image", Summary: "上传图片", Tags: "文件上传"},
		{Method: "POST", Path: "/api/v1/upload/files", Summary: "批量上传文件", Tags: "文件上传"},
		{Method: "GET", Path: "/api/v1/upload/list", Summary: "获取对象存储文件列表", Tags: "文件上传"},
		{Method: "DELETE", Path: "/api/v1/upload/delete", Summary: "删除文件", Tags: "文件上传"},
		{Method: "POST", Path: "/api/v1/upload/set-public-acl", Summary: "批量设置文件ACL为公共读", Tags: "文件上传"},
	}
}
