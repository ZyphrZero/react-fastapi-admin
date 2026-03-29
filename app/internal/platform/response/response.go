package response

import (
	"encoding/json"
	"net/http"
)

func Success(w http.ResponseWriter, data interface{}, msg string, extras map[string]interface{}) {
	if msg == "" {
		msg = "成功"
	}

	payload := map[string]interface{}{
		"code": http.StatusOK,
		"msg":  msg,
		"data": data,
	}
	for key, value := range extras {
		payload[key] = value
	}

	writeJSON(w, http.StatusOK, payload)
}

func Error(w http.ResponseWriter, status int, msg string, data interface{}) {
	writeJSON(w, status, map[string]interface{}{
		"code": status,
		"msg":  msg,
		"data": data,
	})
}

func NotImplemented(w http.ResponseWriter, msg string) {
	if msg == "" {
		msg = "该接口尚未迁移到 Go 后端"
	}
	Error(w, http.StatusNotImplemented, msg, nil)
}

func writeJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
