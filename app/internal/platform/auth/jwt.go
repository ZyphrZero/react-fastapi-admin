package auth

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"react-go-admin/app/internal/config"
)

const (
	tokenAudience = "react-go-admin"
	tokenIssuer   = "react-go-admin"
)

type Manager struct {
	cfg *config.Config
}

type Claims struct {
	UserID         int64  `json:"user_id"`
	Username       string `json:"username,omitempty"`
	IsSuperuser    bool   `json:"is_superuser,omitempty"`
	TokenType      string `json:"token_type"`
	SessionVersion int    `json:"session_version"`
	jwt.RegisteredClaims
}

func NewManager(cfg *config.Config) *Manager {
	return &Manager{cfg: cfg}
}

func (m *Manager) CreateAccessToken(userID int64, username string, isSuperuser bool, sessionVersion int) (string, error) {
	now := time.Now().UTC()
	claims := Claims{
		UserID:         userID,
		Username:       username,
		IsSuperuser:    isSuperuser,
		TokenType:      "access",
		SessionVersion: sessionVersion,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   fmt.Sprintf("%d", userID),
			Audience:  []string{tokenAudience},
			Issuer:    tokenIssuer,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Duration(m.cfg.JWTAccessTokenExpireMinutes) * time.Minute)),
			ID:        randomTokenID(),
		},
	}

	return m.sign(claims)
}

func (m *Manager) CreateRefreshToken(userID int64, sessionVersion int, refreshTokenJTI string) (string, error) {
	now := time.Now().UTC()
	claims := Claims{
		UserID:         userID,
		TokenType:      "refresh",
		SessionVersion: sessionVersion,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   fmt.Sprintf("%d", userID),
			Audience:  []string{tokenAudience},
			Issuer:    tokenIssuer,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.AddDate(0, 0, m.cfg.JWTRefreshTokenExpireDays)),
			ID:        refreshTokenJTI,
		},
	}

	return m.sign(claims)
}

func (m *Manager) Parse(tokenString, expectedType string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if token.Method.Alg() != m.cfg.JWTAlgorithm {
			return nil, fmt.Errorf("unexpected jwt algorithm: %s", token.Method.Alg())
		}
		return []byte(m.cfg.SecretKey), nil
	}, jwt.WithAudience(tokenAudience), jwt.WithIssuer(tokenIssuer))
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token")
	}
	if claims.TokenType != expectedType {
		return nil, errors.New("invalid token type")
	}

	return claims, nil
}

func (m *Manager) sign(claims Claims) (string, error) {
	token := jwt.NewWithClaims(jwt.GetSigningMethod(m.cfg.JWTAlgorithm), claims)
	return token.SignedString([]byte(m.cfg.SecretKey))
}

func randomTokenID() string {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "fallback-token-id"
	}
	return hex.EncodeToString(buf)
}
