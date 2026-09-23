
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";

import "./Auth.css";

function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  /* =========================================================
     HANDLE INPUT
  ========================================================= */

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });

    setError("");
    setSuccess("");
  };

  /* =========================================================
     LOGIN
  ========================================================= */

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    const email = formData.email.trim();
    const password = formData.password;

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await axios.post(
        "https://ai-bug-analyzer-p2wc.onrender.com/api/auth/login",
        {
          email,
          password,
        }
      );

      if (response.data.success) {
        const user = response.data.user;

        localStorage.setItem("isLoggedIn", "true");
        localStorage.setItem("userId", String(user.id));
        localStorage.setItem("userName", user.name || "");
        localStorage.setItem("userEmail", user.email || "");
        localStorage.setItem("userRole", user.role || "user");

        window.dispatchEvent(new Event("loginStatusChanged"));

        setSuccess("Login successful!");

        setTimeout(() => {
          if (user.role === "admin") {
            navigate("/admin");
          } else {
            navigate("/analyzer");
          }
        }, 700);
      }
    } catch (error) {
      console.error("Login error:", error);

      if (error.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError(
          "Unable to connect to the backend. Make sure Flask is running."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  /* =========================================================
     UI
  ========================================================= */

  return (
    <main className="auth-page">
      <div className="auth-card">

        {/* LOGO */}
        <div className="auth-logo">
          <div className="auth-logo-icon">
            AI
          </div>
        </div>

        {/* HEADER */}
        <div className="auth-header">
          <h1>Welcome Back</h1>

          <p>
            Sign in to continue to AI Software Bug Analyzer
          </p>
        </div>

        {/* LOGIN FORM */}
        <form onSubmit={handleSubmit}>

          {/* EMAIL */}
          <div className="form-group">
            <label htmlFor="email">
              Email Address
            </label>

            <input
              id="email"
              type="email"
              name="email"
              placeholder="Enter your email address"
              value={formData.email}
              onChange={handleChange}
              autoComplete="email"
            />
          </div>

          {/* PASSWORD */}
          <div className="form-group">

            <label htmlFor="password">
              Password
            </label>

            <div className="password-wrapper">

              <input
                id="password"
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handleChange}
                autoComplete="current-password"
              />

              {/* EYE BUTTON */}
              <button
                type="button"
                className="password-toggle"
                onClick={() =>
                  setShowPassword((previous) => !previous)
                }
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
                title={
                  showPassword ? "Hide password" : "Show password"
                }
              >
                {showPassword ? (
                  <svg
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M3 3L21 21"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />

                    <path
                      d="M10.6 10.6C10.22 10.98 10 11.47 10 12C10 13.1 10.9 14 12 14C12.53 14 13.02 13.78 13.4 13.4"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />

                    <path
                      d="M6.72 6.72C4.9 7.99 3.47 9.77 2.5 12C4.12 15.45 7.57 18 12 18C13.55 18 14.96 17.67 16.22 17.1"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    <path
                      d="M9.88 5.2C10.56 5.07 11.27 5 12 5C16.43 5 19.88 7.55 21.5 12C21.1 12.85 20.6 13.65 19.98 14.38"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <svg
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M2.5 12C4.12 8.55 7.57 6 12 6C16.43 6 19.88 8.55 21.5 12C19.88 15.45 16.43 18 12 18C7.57 18 4.12 15.45 2.5 12Z"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    <circle
                      cx="12"
                      cy="12"
                      r="2.8"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    />
                  </svg>
                )}
              </button>

            </div>

            {/* FORGOT PASSWORD LINK — below the input */}
            <div className="forgot-password-link">
              <Link to="/forgot-password">
                Forgot Password?
              </Link>
            </div>

          </div>

          {/* ERROR */}
          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {/* SUCCESS */}
          {success && (
            <div className="auth-success">
              {success}
            </div>
          )}

          {/* SUBMIT */}
          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

        </form>

        {/* FOOTER */}
        <div className="auth-footer">
          <p>
            Don't have an account?{" "}
            <Link to="/signup">
              Create Account
            </Link>
          </p>
        </div>

      </div>
    </main>
  );
}

export default Login;

