package base

import (
	"context"

	"react-go-admin/app/internal/platform/password"
)

// EffectivePasswordPolicy returns the runtime password policy as a typed struct.
func (s *Service) EffectivePasswordPolicy(ctx context.Context) password.Policy {
	settings := s.loadSecuritySettings(ctx)
	return password.Policy{
		MinLength:        settings.PasswordMinLength,
		RequireUppercase: settings.PasswordRequireUppercase,
		RequireLowercase: settings.PasswordRequireLowercase,
		RequireDigits:    settings.PasswordRequireDigits,
		RequireSpecial:   settings.PasswordRequireSpecial,
	}
}
