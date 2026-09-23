
import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

import "./Auth.css";

function ForgotPassword() {
  const [email, setEmail] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    if (!emailPattern.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }

    try {
      setLoading(true);

      const response = await axios.post(
        "https://ai-bug-analyzer-p2wc.onrender.com/api/auth/forgot-password",
        {
          email: email.trim(),
        }
      );

      if (response.data.success) {
        setSuccess(
          response.data.message ||
            "A password reset link has been sent to your email."
        );

        setEmail("");
      } else {
        setError(
          response.data.message ||
            "Unable to process password reset request."
        );
      }
    } catch (error) {
      console.error("Forgot password error:", error);

      if (
        error.response &&
        error.response.data &&
        error.response.data.message
      ) {
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

  return (
    <main className="auth-page">
      <div className="auth-card">

        <div className="auth-logo">
          <div className="auth-logo-icon">
            AI
          </div>
        </div>

        <div className="auth-header">
          <h1>Forgot Password</h1>

          <p>
            Enter your email address and we will send you
            a password reset link.
          </p>
        </div>

        <form onSubmit={handleSubmit}>

          <div className="form-group">

            <label htmlFor="email">
              Email Address
            </label>

            <input
              id="email"
              type="email"
              name="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError("");
                setSuccess("");
              }}
              autoComplete="email"
            />

          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {success && (
            <div className="auth-success">
              {success}
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Sending..."
              : "Send Reset Link"}
          </button>

        </form>

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

export default ForgotPassword;
