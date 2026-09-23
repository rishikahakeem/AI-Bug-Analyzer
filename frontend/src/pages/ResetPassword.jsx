/* eslint-disable react-hooks/static-components */

import { useState } from "react";
import {
  Link,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import axios from "axios";

import "./Auth.css";

function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // =========================================================
  // TOKEN FROM RESET LINK
  // =========================================================

  const token = searchParams.get("token") || "";

  // =========================================================
  // STATE
  // =========================================================

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // =========================================================
  // HANDLE RESET
  // =========================================================

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    // -------------------------------------------------------
    // CHECK TOKEN
    // -------------------------------------------------------

    if (!token) {
      setError(
        "Invalid or missing password reset link."
      );
      return;
    }

    // -------------------------------------------------------
    // CHECK NEW PASSWORD
    // -------------------------------------------------------

    if (!password) {
      setError("Please enter a new password.");
      return;
    }

    if (password.length < 6) {
      setError(
        "Password must be at least 6 characters."
      );
      return;
    }

    // -------------------------------------------------------
    // CHECK CONFIRM PASSWORD
    // -------------------------------------------------------

    if (!confirmPassword) {
      setError(
        "Please confirm your new password."
      );
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    // -------------------------------------------------------
    // API REQUEST
    // -------------------------------------------------------

    try {
      setLoading(true);

      const response = await axios.post(
        "http://127.0.0.1:5000/api/auth/reset-password",
        {
          token: token,
          password: password,
        }
      );

      // -----------------------------------------------------
      // SUCCESS
      // -----------------------------------------------------

      if (response.data.success) {
        setSuccess(
          "Password reset successfully! Redirecting to login..."
        );

        setPassword("");
        setConfirmPassword("");

        setTimeout(() => {
          navigate("/login");
        }, 1500);
      } else {
        setError(
          response.data.message ||
            "Unable to reset password."
        );
      }
    } catch (error) {
      console.error(
        "Reset password error:",
        error
      );

      if (
        error.response?.data?.message
      ) {
        setError(
          error.response.data.message
        );
      } else {
        setError(
          "Unable to connect to the backend. Make sure Flask is running."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // PROFESSIONAL EYE ICON
  // =========================================================

  const EyeIcon = ({ crossed = false }) => {
    if (crossed) {
      return (
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
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
      );
    }

    return (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
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
    );
  };

  // =========================================================
  // UI
  // =========================================================

  return (
    <main className="auth-page">
      <div className="auth-card">

        {/* ===================================================
            LOGO
        =================================================== */}

        <div className="auth-logo">
          <div className="auth-logo-icon">
            AI
          </div>
        </div>

        {/* ===================================================
            HEADER
        =================================================== */}

        <div className="auth-header">
          <h1>Reset Password</h1>

          <p>
            Create a new password for your account
          </p>
        </div>

        {/* ===================================================
            FORM
        =================================================== */}

        <form onSubmit={handleSubmit}>

          {/* =================================================
              NEW PASSWORD
          ================================================= */}

          <div className="form-group">
            <label htmlFor="password">
              New Password
            </label>

            <div className="password-wrapper">

              <input
                id="password"
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                name="password"
                placeholder="Enter new password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                  setSuccess("");
                }}
                autoComplete="new-password"
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() =>
                  setShowPassword(
                    (previous) => !previous
                  )
                }
                aria-label={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
                title={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
              >
                <EyeIcon
                  crossed={showPassword}
                />
              </button>

            </div>
          </div>

          {/* =================================================
              CONFIRM PASSWORD
          ================================================= */}

          <div className="form-group">
            <label htmlFor="confirmPassword">
              Confirm Password
            </label>

            <div className="password-wrapper">

              <input
                id="confirmPassword"
                type={
                  showConfirmPassword
                    ? "text"
                    : "password"
                }
                name="confirmPassword"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(
                    e.target.value
                  );
                  setError("");
                  setSuccess("");
                }}
                autoComplete="new-password"
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() =>
                  setShowConfirmPassword(
                    (previous) => !previous
                  )
                }
                aria-label={
                  showConfirmPassword
                    ? "Hide password"
                    : "Show password"
                }
                title={
                  showConfirmPassword
                    ? "Hide password"
                    : "Show password"
                }
              >
                <EyeIcon
                  crossed={showConfirmPassword}
                />
              </button>

            </div>
          </div>

          {/* =================================================
              ERROR
          ================================================= */}

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {/* =================================================
              SUCCESS
          ================================================= */}

          {success && (
            <div className="auth-success">
              {success}
            </div>
          )}

          {/* =================================================
              BUTTON
          ================================================= */}

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Resetting..."
              : "Reset Password"}
          </button>

        </form>

        {/* ===================================================
            BACK TO LOGIN
        =================================================== */}

        <div className="auth-footer">
          <p>
            Remember your password?{" "}
            <Link to="/login">
              Back to Login
            </Link>
          </p>
        </div>

      </div>
    </main>
  );
}

export default ResetPassword;
