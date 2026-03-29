package password

import "testing"

func TestPolicyValidate(t *testing.T) {
	tests := []struct {
		name    string
		policy  Policy
		input   string
		wantErr bool
	}{
		{
			name: "accepts strong password",
			policy: Policy{
				MinLength:        8,
				RequireUppercase: true,
				RequireLowercase: true,
				RequireDigits:    true,
				RequireSpecial:   true,
			},
			input:   "Admin@123",
			wantErr: false,
		},
		{
			name: "rejects missing uppercase",
			policy: Policy{
				MinLength:        8,
				RequireUppercase: true,
				RequireLowercase: true,
				RequireDigits:    true,
				RequireSpecial:   true,
			},
			input:   "admin@123",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.policy.Validate(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
