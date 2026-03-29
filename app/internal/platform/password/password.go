package password

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"regexp"

	"golang.org/x/crypto/bcrypt"

	"react-go-admin/app/internal/config"
)

var (
	uppercasePattern = regexp.MustCompile(`[A-Z]`)
	lowercasePattern = regexp.MustCompile(`[a-z]`)
	digitPattern     = regexp.MustCompile(`[0-9]`)
	specialPattern   = regexp.MustCompile(`[^A-Za-z0-9]`)
)

const bootstrapCharacterSet = "0123456789!@#$%^&*()-_=+[]{};:,.?/"

type Policy struct {
	MinLength        int  `json:"password_min_length"`
	RequireUppercase bool `json:"password_require_uppercase"`
	RequireLowercase bool `json:"password_require_lowercase"`
	RequireDigits    bool `json:"password_require_digits"`
	RequireSpecial   bool `json:"password_require_special"`
}

func NewPolicy(cfg *config.Config) Policy {
	return Policy{
		MinLength:        cfg.PasswordMinLength,
		RequireUppercase: cfg.PasswordRequireUppercase,
		RequireLowercase: cfg.PasswordRequireLowercase,
		RequireDigits:    cfg.PasswordRequireDigits,
		RequireSpecial:   cfg.PasswordRequireSpecial,
	}
}

func (p Policy) Validate(raw string) error {
	if len(raw) < p.MinLength {
		return fmt.Errorf("密码长度不能少于 %d 位", p.MinLength)
	}
	if p.RequireUppercase && !uppercasePattern.MatchString(raw) {
		return fmt.Errorf("密码必须包含至少一个大写字母")
	}
	if p.RequireLowercase && !lowercasePattern.MatchString(raw) {
		return fmt.Errorf("密码必须包含至少一个小写字母")
	}
	if p.RequireDigits && !digitPattern.MatchString(raw) {
		return fmt.Errorf("密码必须包含至少一个数字")
	}
	if p.RequireSpecial && !specialPattern.MatchString(raw) {
		return fmt.Errorf("密码必须包含至少一个特殊字符")
	}
	return nil
}

func Hash(raw string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(raw), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

func Verify(raw, hashed string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(raw)) == nil
}

func GenerateBootstrapPassword(length int) (string, error) {
	if length < 2 {
		length = 12
	}
	result := make([]byte, 0, length)
	for len(result) < length {
		index, err := rand.Int(rand.Reader, big.NewInt(int64(len(bootstrapCharacterSet))))
		if err != nil {
			return "", err
		}
		result = append(result, bootstrapCharacterSet[index.Int64()])
	}
	return string(result), nil
}
