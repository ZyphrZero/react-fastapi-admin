package base

import "sort"

type menuItem struct {
	ID        int         `json:"id"`
	Name      string      `json:"name"`
	Path      string      `json:"path"`
	Icon      string      `json:"icon"`
	Order     int         `json:"order"`
	ParentID  int         `json:"parent_id"`
	IsHidden  bool        `json:"is_hidden"`
	Component string      `json:"component"`
	Keepalive bool        `json:"keepalive"`
	Redirect  interface{} `json:"redirect"`
	Children  []menuItem  `json:"children"`
}

type MenuItem = menuItem

var fullMenuTree = []menuItem{
	{
		ID:        1,
		Name:      "工作台",
		Path:      "/dashboard",
		Icon:      "material-symbols:dashboard-outline",
		Order:     0,
		ParentID:  0,
		IsHidden:  false,
		Component: "/dashboard",
		Keepalive: false,
		Redirect:  nil,
	},
	{
		ID:        10,
		Name:      "系统管理",
		Path:      "/system",
		Icon:      "carbon:gui-management",
		Order:     1,
		ParentID:  0,
		IsHidden:  false,
		Component: "Layout",
		Keepalive: false,
		Redirect:  "/system/users",
		Children: []menuItem{
			{
				ID:        11,
				Name:      "用户管理",
				Path:      "/system/users",
				Icon:      "ph:user-list-bold",
				Order:     1,
				ParentID:  10,
				IsHidden:  false,
				Component: "/system/users",
				Keepalive: false,
				Redirect:  nil,
			},
			{
				ID:        12,
				Name:      "角色管理",
				Path:      "/system/roles",
				Icon:      "carbon:user-role",
				Order:     2,
				ParentID:  10,
				IsHidden:  false,
				Component: "/system/roles",
				Keepalive: false,
				Redirect:  nil,
			},
			{
				ID:        13,
				Name:      "API管理",
				Path:      "/system/apis",
				Icon:      "ant-design:api-outlined",
				Order:     3,
				ParentID:  10,
				IsHidden:  false,
				Component: "/system/apis",
				Keepalive: false,
				Redirect:  nil,
			},
			{
				ID:        15,
				Name:      "审计日志",
				Path:      "/system/audit",
				Icon:      "ph:clipboard-text-bold",
				Order:     4,
				ParentID:  10,
				IsHidden:  false,
				Component: "/system/audit",
				Keepalive: false,
				Redirect:  nil,
			},
		},
	},
}

func cloneMenu(items []menuItem) []menuItem {
	result := make([]menuItem, 0, len(items))
	for _, item := range items {
		nextItem := item
		nextItem.Children = cloneMenu(item.Children)
		result = append(result, nextItem)
	}
	return result
}

func filterMenu(items []menuItem, allowed map[string]struct{}) []menuItem {
	result := make([]menuItem, 0, len(items))
	for _, item := range items {
		children := filterMenu(item.Children, allowed)
		_, ok := allowed[item.Path]
		if !ok && len(children) == 0 {
			continue
		}
		nextItem := item
		nextItem.Children = children
		if len(children) > 0 {
			nextItem.Redirect = children[0].Path
		}
		result = append(result, nextItem)
	}
	return result
}

func assignableMenuTree() []menuItem {
	return cloneMenu(fullMenuTree)
}

func AssignableMenuTree() []MenuItem {
	return assignableMenuTree()
}

func defaultRoleMenuPaths(roleName string) []string {
	switch roleName {
	case "管理员":
		return []string{"/dashboard", "/system/users", "/system/roles", "/system/apis", "/system/audit"}
	case "普通用户":
		return []string{"/dashboard"}
	default:
		return []string{}
	}
}

func DefaultRoleMenuPaths(roleName string) []string {
	return defaultRoleMenuPaths(roleName)
}

func findUnknownMenuPaths(menuPaths []string) []string {
	known := map[string]struct{}{}
	walkMenuTree(fullMenuTree, func(item menuItem) {
		known[item.Path] = struct{}{}
	})
	unknown := make([]string, 0)
	seen := map[string]struct{}{}
	for _, path := range menuPaths {
		if _, ok := known[path]; ok {
			continue
		}
		if _, ok := seen[path]; ok {
			continue
		}
		seen[path] = struct{}{}
		unknown = append(unknown, path)
	}
	sort.Strings(unknown)
	return unknown
}

func FindUnknownMenuPaths(menuPaths []string) []string {
	return findUnknownMenuPaths(menuPaths)
}

func normalizeMenuPaths(menuPaths []string) []string {
	if len(menuPaths) == 0 {
		return []string{}
	}
	leafSet := map[string]struct{}{}
	for _, path := range menuPaths {
		collectNormalizedMenuPaths(fullMenuTree, path, leafSet)
	}
	result := make([]string, 0, len(leafSet))
	for path := range leafSet {
		result = append(result, path)
	}
	sort.Strings(result)
	return result
}

func NormalizeMenuPaths(menuPaths []string) []string {
	return normalizeMenuPaths(menuPaths)
}

func collectNormalizedMenuPaths(items []menuItem, targetPath string, output map[string]struct{}) bool {
	for _, item := range items {
		if item.Path == targetPath {
			collectLeafPaths(item, output)
			return true
		}
		if collectNormalizedMenuPaths(item.Children, targetPath, output) {
			return true
		}
	}
	return false
}

func collectLeafPaths(item menuItem, output map[string]struct{}) {
	if len(item.Children) == 0 {
		output[item.Path] = struct{}{}
		return
	}
	for _, child := range item.Children {
		collectLeafPaths(child, output)
	}
}

func walkMenuTree(items []menuItem, visit func(menuItem)) {
	for _, item := range items {
		visit(item)
		walkMenuTree(item.Children, visit)
	}
}
