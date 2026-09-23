import { useEffect, useState } from "react";
import {
  Link,
  NavLink,
  useNavigate,
} from "react-router";

import {
  FaBug,
  FaGithub,
  FaArrowRight,
  FaSignInAlt,
  FaUserPlus,
  FaUserCircle,
  FaSignOutAlt,
  FaMoon,
  FaSun,
  FaUserShield,
} from "react-icons/fa";

function Navbar() {
  const navigate = useNavigate();

  // =========================================================
  // LOGIN STATE
  // =========================================================

  const [isLoggedIn, setIsLoggedIn] = useState(
    localStorage.getItem("isLoggedIn") === "true"
  );

  const [userName, setUserName] = useState(
    localStorage.getItem("userName") || ""
  );

  const [userRole, setUserRole] = useState(
    localStorage.getItem("userRole") || "user"
  );

  // =========================================================
  // THEME STATE
  // =========================================================

  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem("theme");
    return savedTheme === "dark" ? "dark" : "light";
  });

  // =========================================================
  // APPLY THEME
  // =========================================================

  useEffect(() => {
    document.documentElement.classList.toggle(
      "dark-mode",
      theme === "dark"
    );
    localStorage.setItem("theme", theme);
  }, [theme]);

  // =========================================================
  // UPDATE NAVBAR AFTER LOGIN / LOGOUT
  // =========================================================

  useEffect(() => {
    const updateAuth = () => {
      const loggedIn =
        localStorage.getItem("isLoggedIn") === "true";
      const name =
        localStorage.getItem("userName") || "";
      const role =
        localStorage.getItem("userRole") || "user";

      setIsLoggedIn(loggedIn);
      setUserName(name);
      setUserRole(role);
    };

    window.addEventListener(
      "loginStatusChanged",
      updateAuth
    );

    window.addEventListener(
      "storage",
      updateAuth
    );

    return () => {
      window.removeEventListener(
        "loginStatusChanged",
        updateAuth
      );

      window.removeEventListener(
        "storage",
        updateAuth
      );
    };
  }, []);

  // =========================================================
  // LOGOUT
  // =========================================================

  const handleLogout = () => {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userId");
    localStorage.removeItem("userName");
    localStorage.removeItem("userEmail");
    localStorage.removeItem("userRole");

    setIsLoggedIn(false);
    setUserName("");
    setUserRole("user");

    window.dispatchEvent(
      new Event("loginStatusChanged")
    );

    navigate("/");
  };

  // =========================================================
  // THEME TOGGLE
  // =========================================================

  const toggleTheme = () => {
    setTheme((currentTheme) =>
      currentTheme === "light"
        ? "dark"
        : "light"
    );
  };

  // =========================================================
  // NAVBAR
  // =========================================================

  return (
    <nav className="navbar">

      {/* LOGO */}

      <Link
        to="/"
        className="logo"
      >
        <div className="logo-icon">
          <FaBug />
        </div>

        <div className="logo-text">
          <strong>
            Bug<span>AI</span>
          </strong>

          <small>
            CODE INTELLIGENCE
          </small>
        </div>
      </Link>

      {/* MAIN NAVIGATION */}

      <div className="nav-links">

        <NavLink
          to="/"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Home
        </NavLink>

        <NavLink
          to="/analyzer"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Analyzer
        </NavLink>

        <NavLink
          to="/features"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Features
        </NavLink>

        <NavLink
          to="/history"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          History
        </NavLink>

        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Dashboard
        </NavLink>

        <NavLink
          to="/profile"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Profile
        </NavLink>

        {isLoggedIn && userRole === "admin" && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              isActive ? "active" : ""
            }
          >
            Admin
          </NavLink>
        )}

      </div>

      {/* RIGHT SIDE */}

      <div className="nav-actions">

        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          title={
            theme === "light"
              ? "Switch to dark mode"
              : "Switch to light mode"
          }
          aria-label={
            theme === "light"
              ? "Switch to dark mode"
              : "Switch to light mode"
          }
        >
          {theme === "light" ? (
            <FaMoon />
          ) : (
            <FaSun />
          )}
        </button>

        <a
          href="https://github.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="github-link"
          title="GitHub"
        >
          <FaGithub />
        </a>

        {!isLoggedIn && (
          <>
            <Link
              to="/login"
              className="login-nav-button"
            >
              <FaSignInAlt />
              <span>Login</span>
            </Link>

            <Link
              to="/signup"
              className="signup-nav-button"
            >
              <FaUserPlus />
              <span>Sign Up</span>
            </Link>
          </>
        )}

        {isLoggedIn && (
          <>
            <Link
              to="/profile"
              className="user-nav"
              title="View Profile"
            >
              <FaUserCircle />
              <span>{userName || "User"}</span>
            </Link>

            {userRole === "admin" && (
              <Link
                to="/admin"
                className="admin-nav-button"
                title="Admin Dashboard"
              >
                <FaUserShield />
                <span>Admin</span>
              </Link>
            )}

            <button
              type="button"
              className="logout-nav-button"
              onClick={handleLogout}
            >
              <FaSignOutAlt />
              <span>Logout</span>
            </button>
          </>
        )}

        <Link
          to="/analyzer"
          className="nav-button"
        >
          <span>Start Analyzing</span>
          <FaArrowRight />
        </Link>

      </div>

    </nav>
  );
}

export default Navbar;