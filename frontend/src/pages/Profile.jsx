/* eslint-disable react-hooks/set-state-in-effect */
/* eslint-disable react-hooks/immutability */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import {
  FaUserCircle,
  FaEnvelope,
  FaIdCard,
  FaCode,
  FaSignOutAlt,
  FaArrowLeft,
} from "react-icons/fa";

import "./Profile.css";

function Profile() {
  const navigate = useNavigate();

  const [userName, setUserName] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [userId, setUserId] = useState("");
  const [analysisCount, setAnalysisCount] = useState(0);

  useEffect(() => {
    const loggedIn =
      localStorage.getItem("isLoggedIn") === "true";

    if (!loggedIn) {
      navigate("/login");
      return;
    }

    setUserName(
      localStorage.getItem("userName") || "User"
    );

    setUserEmail(
      localStorage.getItem("userEmail") || "Not available"
    );

    setUserId(
      localStorage.getItem("userId") || "Not available"
    );

    fetchAnalysisCount();
  }, [navigate]);

  const fetchAnalysisCount = async () => {
    try {
      const id = localStorage.getItem("userId");

      if (!id) {
        return;
      }

      const response = await axios.get(
        `https://ai-bug-analyzer-p2wc.onrender.com/api/history/${id}`
      );

      const history =
        response.data?.analyses ||
        response.data?.history ||
        response.data?.data ||
        [];

      setAnalysisCount(history.length);
    } catch (error) {
      console.error(
        "Failed to load analysis count:",
        error
      );
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userId");
    localStorage.removeItem("userName");
    localStorage.removeItem("userEmail");

    window.dispatchEvent(
      new Event("loginStatusChanged")
    );

    navigate("/");
  };

  return (
    <main className="profile-page">

      <div className="profile-container">

        {/* BACK */}

        <button
          type="button"
          className="profile-back-button"
          onClick={() => navigate(-1)}
        >
          <FaArrowLeft />
          <span>Back</span>
        </button>

        {/* HEADER */}

        <div className="profile-header">
          <span>ACCOUNT</span>

          <h1>My Profile</h1>

          <p>
            Manage your BugAI account information and
            view your analysis activity.
          </p>
        </div>

        {/* USER CARD */}

        <section className="profile-user-card">

          <div className="profile-avatar">
            <FaUserCircle />
          </div>

          <div className="profile-user-info">
            <h2>{userName}</h2>

            <p>{userEmail}</p>
          </div>

        </section>

        {/* DETAILS */}

        <section className="profile-details-grid">

          {/* FULL NAME */}

          <article className="profile-detail-card profile-name-card">

            <div className="profile-detail-icon">
              <FaUserCircle />
            </div>

            <div className="profile-detail-content">
              <span>Full Name</span>

              <strong>
                {userName}
              </strong>
            </div>

          </article>

          {/* EMAIL */}

          <article className="profile-detail-card profile-email-card">

            <div className="profile-detail-icon">
              <FaEnvelope />
            </div>

            <div className="profile-detail-content">
              <span>Email Address</span>

              <strong>
                {userEmail}
              </strong>
            </div>

          </article>

          {/* USER ID */}

          <article className="profile-detail-card profile-id-card">

            <div className="profile-detail-icon">
              <FaIdCard />
            </div>

            <div className="profile-detail-content">
              <span>User ID</span>

              <strong>
                {userId}
              </strong>
            </div>

          </article>

          {/* ANALYSES */}

          <article className="profile-detail-card profile-analysis-card">

            <div className="profile-detail-icon">
              <FaCode />
            </div>

            <div className="profile-detail-content">
              <span>Total Analyses</span>

              <strong>
                {analysisCount}
              </strong>
            </div>

          </article>

        </section>

        {/* LOGOUT */}

        <div className="profile-actions">

          <button
            type="button"
            className="profile-logout-button"
            onClick={handleLogout}
          >
            <FaSignOutAlt />
            Logout
          </button>

        </div>

      </div>

    </main>
  );
}

export default Profile;