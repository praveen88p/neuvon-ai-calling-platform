import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Phone, Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Left side — Form */}
      <div className="login-form-side">
        <div className="login-form-container">
          {/* Brand */}
          <div className="login-brand">
            <div className="login-brand-icon">
              <Phone className="h-5 w-5" />
            </div>
            <span className="login-brand-name">Neuvon</span>
          </div>

          {/* Heading */}
          <div className="login-heading">
            <h1>Welcome back</h1>
            <p>Sign in to your account to continue</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <Alert variant="destructive" className="login-alert">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="login-field">
              <Label htmlFor="login-email" className="login-label">
                Email Address
              </Label>
              <Input
                id="login-email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="login-input"
                autoComplete="email"
              />
            </div>

            <div className="login-field">
              <Label htmlFor="login-password" className="login-label">
                Password
              </Label>
              <div className="login-password-wrapper">
                <Input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="login-input login-input-password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-password-toggle"
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

            <Button
              type="submit"
              className="login-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>

            <p className="login-footer-text">
              Don't have an account?{" "}
              <Link to="/register" className="login-link">
                Create one
              </Link>
            </p>
          </form>
        </div>

        {/* Bottom tagline */}
        <p className="login-tagline">AI-powered voice calling platform</p>
      </div>

      {/* Right side — Visual */}
      <div className="login-visual-side">
        <div className="login-visual-content">
          {/* Animated gradient blobs */}
          <div className="login-blob login-blob-1" />
          <div className="login-blob login-blob-2" />
          <div className="login-blob login-blob-3" />

          {/* Floating grid overlay */}
          <div className="login-grid-overlay" />

          {/* Feature highlights */}
          <div className="login-visual-text">
            <h2>Automate your outreach with AI voice agents</h2>
            <div className="login-feature-list">
              <div className="login-feature-item">
                <div className="login-feature-dot" />
                <span>Bulk AI-powered voice campaigns</span>
              </div>
              <div className="login-feature-item">
                <div className="login-feature-dot" />
                <span>Real-time call analytics & transcripts</span>
              </div>
              <div className="login-feature-item">
                <div className="login-feature-dot" />
                <span>Google Sheets & CRM integrations</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
