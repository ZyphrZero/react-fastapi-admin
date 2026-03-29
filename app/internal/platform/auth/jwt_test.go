package auth

import (
	"testing"

	"react-go-admin/app/internal/config"
)

func TestManagerRoundTrip(t *testing.T) {
	cfg := &config.Config{
		SecretKey:                   "0123456789abcdef0123456789abcdef",
		JWTAlgorithm:                "HS256",
		JWTAccessTokenExpireMinutes: 15,
		JWTRefreshTokenExpireDays:   7,
	}

	manager := NewManager(cfg)
	token, err := manager.CreateAccessToken(42, "admin", true, 3)
	if err != nil {
		t.Fatalf("CreateAccessToken() error = %v", err)
	}

	claims, err := manager.Parse(token, "access")
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}

	if claims.UserID != 42 || claims.Username != "admin" || !claims.IsSuperuser || claims.SessionVersion != 3 {
		t.Fatalf("unexpected claims: %+v", claims)
	}
}
