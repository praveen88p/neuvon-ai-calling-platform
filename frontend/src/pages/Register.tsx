import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Phone, Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";

export default function Register() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    organization_name: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!formData.full_name.trim()) {
      setError("Full name is required");
      return;
    }

    if (!formData.organization_name.trim()) {
      setError("Organization name is required");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsLoading(true);

    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        organization_name: formData.organization_name,
      });
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-page">
      {/* Left side — Form */}
      <div className="register-form-side">
        <div className="register-form-container">
          {/* Brand */}
          <div className="register-brand">
            <div className="register-brand-icon">
              <Phone className="h-5 w-5" />
            </div>
            <span className="register-brand-name">Neuvon</span>
          </div>

          {/* Heading */}
          <div className="register-heading">
            <h1>Create an account</h1>
            <p>Set up your organization to get started</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="register-form">
            {error && (
              <Alert variant="destructive" className="register-alert">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="register-field-row">
              <div className="register-field">
                <Label htmlFor="reg-full_name" className="register-label">
                  Full Name
                </Label>
                <Input
                  id="reg-full_name"
                  name="full_name"
                  type="text"
                  placeholder="John Doe"
                  value={formData.full_name}
                  onChange={handleChange}
                  required
                  className="register-input"
                  autoComplete="name"
                />
              </div>

              <div className="register-field">
                <Label htmlFor="reg-organization" className="register-label">
                  Organization
                </Label>
                <Input
                  id="reg-organization"
                  name="organization_name"
                  type="text"
                  placeholder="Acme Inc."
                  value={formData.organization_name}
                  onChange={handleChange}
                  required
                  className="register-input"
                  autoComplete="organization"
                />
              </div>
            </div>

            <div className="register-field">
              <Label htmlFor="reg-email" className="register-label">
                Email Address
              </Label>
              <Input
                id="reg-email"
                name="email"
                type="email"
                placeholder="you@company.com"
                value={formData.email}
                onChange={handleChange}
                required
                className="register-input"
                autoComplete="email"
              />
            </div>

            <div className="register-field">
              <Label htmlFor="reg-password" className="register-label">
                Password
              </Label>
              <div className="register-password-wrapper">
                <Input
                  id="reg-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Min. 8 characters"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="register-input register-input-password"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="register-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="register-field">
              <Label htmlFor="reg-confirmPassword" className="register-label">
                Confirm Password
              </Label>
              <div className="register-password-wrapper">
                <Input
                  id="reg-confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  className="register-input register-input-password"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="register-password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  tabIndex={-1}
                  aria-label={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="register-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Create account"
              )}
            </Button>

            <p className="register-footer-text">
              Already have an account?{" "}
              <Link to="/login" className="register-link">
                Sign in
              </Link>
            </p>
          </form>
        </div>

        {/* Bottom tagline */}
        <p className="register-tagline">AI-powered voice calling platform</p>
      </div>

      {/* Right side — Visual */}
      <div className="register-visual-side">
        <div className="register-visual-content">
          {/* Animated gradient blobs */}
          <div className="register-blob register-blob-1" />
          <div className="register-blob register-blob-2" />
          <div className="register-blob register-blob-3" />

          {/* Floating grid overlay */}
          <div className="register-grid-overlay" />

          {/* Feature highlights */}
          <div className="register-visual-text">
            <h2>Start automating your voice outreach today</h2>
            <div className="register-feature-list">
              <div className="register-feature-item">
                <div className="register-feature-dot" />
                <span>Free trial with no credit card required</span>
              </div>
              <div className="register-feature-item">
                <div className="register-feature-dot" />
                <span>Set up your first campaign in minutes</span>
              </div>
              <div className="register-feature-item">
                <div className="register-feature-dot" />
                <span>Built-in AI agent configuration</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
