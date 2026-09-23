import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

import {
  FaUsers,
  FaCode,
  FaLanguage,
  FaHistory,
  FaUserShield,
  FaExclamationTriangle,
  FaArrowLeft,
} from "react-icons/fa";

import "./Admin.css";


function Admin() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [admin, setAdmin] = useState(null);

  const [stats, setStats] = useState({
    total_users: 0,
    total_analyses: 0,
  });

  const [languageStats, setLanguageStats] = useState([]);
  const [recentUsers, setRecentUsers] = useState([]);
  const [recentAnalyses, setRecentAnalyses] = useState([]);


  // =========================================================
  // FETCH ADMIN DATA
  // =========================================================

  useEffect(() => {
    const fetchAdminDashboard = async () => {
      try {
        setLoading(true);
        setError("");

        const userId = localStorage.getItem("userId");
        const loggedIn =
          localStorage.getItem("isLoggedIn") === "true";

        if (!loggedIn || !userId) {
          navigate("/login");
          return;
        }

        const response = await axios.get(
          `http://127.0.0.1:5000/api/admin/dashboard/${userId}`
        );

        if (!response.data?.success) {
          setError(
            response.data?.message ||
              "Unable to load admin dashboard."
          );
          return;
        }

        setAdmin(response.data.admin || null);

        setStats(
          response.data.stats || {
            total_users: 0,
            total_analyses: 0,
          }
        );

        setLanguageStats(
          response.data.language_stats || []
        );

        setRecentUsers(
          response.data.recent_users || []
        );

        setRecentAnalyses(
          response.data.recent_analyses || []
        );
      } catch (err) {
        console.error(
          "Admin dashboard error:",
          err
        );

        if (err.response?.status === 403) {
          setError(
            "You do not have permission to access the Admin Dashboard."
          );
        } else if (err.response?.status === 404) {
          setError(
            "Admin user was not found."
          );
        } else {
          setError(
            err.response?.data?.message ||
              "Unable to connect to the backend."
          );
        }
      } finally {
        setLoading(false);
      }
    };

    fetchAdminDashboard();
  }, [navigate]);


  // =========================================================
  // FORMAT DATE
  // =========================================================

  const formatDate = (date) => {
    if (!date) {
      return "N/A";
    }

    try {
      return new Date(date).toLocaleString(
        "en-IN",
        {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          hour12: true,
        }
      );
    } catch {
      return String(date);
    }
  };


  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <main className="admin-page">

        <div className="admin-loading">

          <div className="admin-spinner"></div>

          <h2>
            Loading Admin Dashboard
          </h2>

          <p>
            Please wait while we load the
            administration data.
          </p>

        </div>

      </main>
    );
  }


  // =========================================================
  // ERROR
  // =========================================================

  if (error) {
    return (
      <main className="admin-page">

        <div className="admin-error">

          <FaExclamationTriangle />

          <h2>
            Admin Access
          </h2>

          <p>
            {error}
          </p>

          <button
            type="button"
            onClick={() => navigate("/")}
          >
            Go Home
          </button>

        </div>

      </main>
    );
  }


  // =========================================================
  // ADMIN DASHBOARD
  // =========================================================

  return (
    <main className="admin-page">

      <div className="admin-container">

        {/* ===================================================
            BACK
        =================================================== */}

        <button
          type="button"
          className="admin-back-button"
          onClick={() => navigate(-1)}
        >
          <FaArrowLeft />
          Back
        </button>


        {/* ===================================================
            HEADER
        =================================================== */}

        <div className="admin-header">

          <div className="admin-heading">

            <span>
              ADMINISTRATION
            </span>

            <h1>
              Admin Dashboard
            </h1>

            <p>
              Monitor users, analyses and
              application activity.
            </p>

          </div>


          <div className="admin-profile">

            <div className="admin-profile-icon">
              <FaUserShield />
            </div>

            <div>
              <strong>
                {admin?.name || "Admin"}
              </strong>

              <span>
                {admin?.email || ""}
              </span>

              <small>
                ADMIN
              </small>
            </div>

          </div>

        </div>


        {/* ===================================================
            STAT CARDS
        =================================================== */}

        <section className="admin-stats">

          <div className="admin-stat-card users">

            <div className="admin-stat-icon">
              <FaUsers />
            </div>

            <div>
              <span>
                Total Users
              </span>

              <strong>
                {stats.total_users}
              </strong>
            </div>

          </div>


          <div className="admin-stat-card analyses">

            <div className="admin-stat-icon">
              <FaCode />
            </div>

            <div>
              <span>
                Total Analyses
              </span>

              <strong>
                {stats.total_analyses}
              </strong>
            </div>

          </div>


          <div className="admin-stat-card languages">

            <div className="admin-stat-icon">
              <FaLanguage />
            </div>

            <div>
              <span>
                Languages
              </span>

              <strong>
                {languageStats.length}
              </strong>
            </div>

          </div>


          <div className="admin-stat-card activity">

            <div className="admin-stat-icon">
              <FaHistory />
            </div>

            <div>
              <span>
                Recent Activity
              </span>

              <strong>
                {recentAnalyses.length}
              </strong>
            </div>

          </div>

        </section>


        {/* ===================================================
            LANGUAGE STATISTICS
        =================================================== */}

        <section className="admin-section">

          <div className="admin-section-heading">

            <div>
              <span>
                ANALYTICS
              </span>

              <h2>
                Analysis by Language
              </h2>
            </div>

          </div>


          {languageStats.length === 0 ? (

            <div className="admin-empty">
              No analysis data available yet.
            </div>

          ) : (

            <div className="language-grid">

              {languageStats.map((item) => (

                <div
                  className="language-card"
                  key={item.language}
                >

                  <div className="language-card-left">

                    <div className="language-dot"></div>

                    <span>
                      {item.language}
                    </span>

                  </div>

                  <strong>
                    {item.count}
                  </strong>

                </div>

              ))}

            </div>

          )}

        </section>


        {/* ===================================================
            RECENT USERS
        =================================================== */}

        <section className="admin-section">

          <div className="admin-section-heading">

            <div>
              <span>
                USERS
              </span>

              <h2>
                Recent Users
              </h2>
            </div>

          </div>


          {recentUsers.length === 0 ? (

            <div className="admin-empty">
              No users found.
            </div>

          ) : (

            <div className="admin-table-wrapper">

              <table className="admin-table">

                <thead>

                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Created</th>
                  </tr>

                </thead>

                <tbody>

                  {recentUsers.map((user) => (

                    <tr key={user.id}>

                      <td>
                        {user.id}
                      </td>

                      <td className="user-name">
                        {user.name}
                      </td>

                      <td>
                        {user.email}
                      </td>

                      <td>

                        <span
                          className={
                            user.role === "admin"
                              ? "role-badge role-admin"
                              : "role-badge role-user"
                          }
                        >
                          {user.role || "user"}
                        </span>

                      </td>

                      <td>
                        {formatDate(user.created_at)}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>


        {/* ===================================================
            RECENT ANALYSES
        =================================================== */}

        <section className="admin-section">

          <div className="admin-section-heading">

            <div>
              <span>
                ACTIVITY
              </span>

              <h2>
                Recent Analyses
              </h2>
            </div>

          </div>


          {recentAnalyses.length === 0 ? (

            <div className="admin-empty">
              No analyses found yet.
            </div>

          ) : (

            <div className="admin-table-wrapper">

              <table className="admin-table">

                <thead>

                  <tr>
                    <th>ID</th>
                    <th>User</th>
                    <th>Email</th>
                    <th>Language</th>
                    <th>Date</th>
                  </tr>

                </thead>

                <tbody>

                  {recentAnalyses.map((item) => (

                    <tr key={item.id}>

                      <td>
                        {item.id}
                      </td>

                      <td className="user-name">
                        {item.user_name || "Unknown"}
                      </td>

                      <td>
                        {item.user_email || "N/A"}
                      </td>

                      <td>

                        <span className="language-badge">
                          {item.language}
                        </span>

                      </td>

                      <td>
                        {formatDate(item.created_at)}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </main>
  );
}

export default Admin;