
/* eslint-disable react-hooks/immutability */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import "./Dashboard.css";

function Dashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const userId = localStorage.getItem("userId");

  useEffect(() => {
    fetchHistory();
  }, []);

  // =====================================================
  // FETCH HISTORY
  // =====================================================

  const fetchHistory = async () => {
    try {
      if (!userId) {
        setLoading(false);
        return;
      }

      const response = await fetch(
        `https://ai-bug-analyzer-p2wc.onrender.com/api/history/${userId}`
      );

      const data = await response.json();

      if (data.success) {
        setHistory(data.analyses || []);
      } else {
        setHistory([]);
      }
    } catch (error) {
      console.error("Error loading dashboard:", error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // GET RESULT TEXT SAFELY
  // =====================================================

  const getResult = (item) => {
    return item.result || "";
  };

  // =====================================================
  // EXTRACT SECTION FROM AI ANALYSIS
  // =====================================================

  const getSection = (result, sectionName) => {
    if (!result) {
      return "";
    }

    const text = String(result).replace(/\r\n/g, "\n");

    const escaped = sectionName.replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&"
    );

    const startPattern = new RegExp(
      `(?:^|\\n)\\s*${escaped}\\s*:?[ \\t]*(?:\\n|$)`,
      "i"
    );

    const startMatch = startPattern.exec(text);

    if (!startMatch) {
      return "";
    }

    const contentStart =
      startMatch.index + startMatch[0].length;

    const remaining = text.slice(contentStart);

    const endMatch = remaining.match(
      /\n[A-Z][A-Z ]{2,}\s*:?[ \t]*(?:\n|$)/
    );

    const endIndex = endMatch
      ? contentStart + endMatch.index
      : text.length;

    return text
      .slice(contentStart, endIndex)
      .trim();
  };

  // =====================================================
  // GET SEVERITY
  // =====================================================

  const getSeverity = (item) => {
    const result = getResult(item);

    const severity = getSection(
      result,
      "SEVERITY"
    );

    if (!severity) {
      return "NONE";
    }

    const firstLine =
      severity
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)[0] || "";

    const upper = firstLine.toUpperCase();

    const allowed = [
      "CRITICAL",
      "HIGH",
      "MEDIUM",
      "LOW",
      "NONE",
    ];

    return allowed.includes(upper)
      ? upper
      : "NONE";
  };

  // =====================================================
  // FORMAT DATE
  // =====================================================

  const formatDate = (dateValue) => {
    if (!dateValue) {
      return "Date unavailable";
    }

    let date;

    if (
      typeof dateValue === "string" &&
      /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(
        dateValue
      )
    ) {
      date = new Date(
        dateValue.replace(" ", "T")
      );
    } else {
      date = new Date(dateValue);
    }

    if (isNaN(date.getTime())) {
      return "Date unavailable";
    }

    return date.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // =====================================================
  // STATISTICS
  // =====================================================

  const totalAnalyses = history.length;

  const criticalCount = history.filter(
    (item) =>
      getSeverity(item) === "CRITICAL"
  ).length;

  const highCount = history.filter(
    (item) =>
      getSeverity(item) === "HIGH"
  ).length;

  const mediumCount = history.filter(
    (item) =>
      getSeverity(item) === "MEDIUM"
  ).length;

  const lowCount = history.filter(
    (item) =>
      getSeverity(item) === "LOW"
  ).length;

  const totalBugs = history.filter(
    (item) =>
      getSeverity(item) !== "NONE"
  ).length;

  // =====================================================
  // RENDER
  // =====================================================

  return (
    <div className="dashboard-page">

      {/* =================================================
          HEADER
          ================================================= */}

      <div className="dashboard-header">

        <div>
          <p className="dashboard-label">
            AI CODE INTELLIGENCE
          </p>

          <h1>
            Dashboard
          </h1>

          <p className="dashboard-description">
            Overview of your AI code analysis activity.
          </p>
        </div>

      </div>

      {/* =================================================
          LOADING
          ================================================= */}

      {loading ? (
        <div className="dashboard-loading">

          <div className="loading-spinner"></div>

          <p>
            Loading dashboard...
          </p>

        </div>
      ) : (
        <>

          {/* =================================================
              STATISTICS
              ================================================= */}

          <div className="dashboard-stats">

            <div className="stat-card">

              <div className="stat-icon blue">
                📊
              </div>

              <div>
                <h3>
                  Total Analyses
                </h3>

                <strong>
                  {totalAnalyses}
                </strong>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon red">
                🐛
              </div>

              <div>
                <h3>
                  Total Bugs
                </h3>

                <strong>
                  {totalBugs}
                </strong>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon critical">
                🔴
              </div>

              <div>
                <h3>
                  Critical
                </h3>

                <strong>
                  {criticalCount}
                </strong>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon high">
                🟠
              </div>

              <div>
                <h3>
                  High
                </h3>

                <strong>
                  {highCount}
                </strong>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon medium">
                🟡
              </div>

              <div>
                <h3>
                  Medium
                </h3>

                <strong>
                  {mediumCount}
                </strong>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon low">
                🟢
              </div>

              <div>
                <h3>
                  Low
                </h3>

                <strong>
                  {lowCount}
                </strong>
              </div>

            </div>

          </div>

          {/* =================================================
              DASHBOARD GRID
              ================================================= */}

          <div className="dashboard-grid">

            {/* =================================================
                SEVERITY OVERVIEW
                ================================================= */}

            <div className="dashboard-card severity-card">

              <div className="card-header">

                <div>
                  <h2>
                    Severity Overview
                  </h2>

                  <p>
                    Distribution of detected bugs
                  </p>
                </div>

                <div className="card-icon">
                  📈
                </div>

              </div>


              <div className="severity-list">

                {/* CRITICAL */}

                <div className="severity-item">

                  <div className="severity-top">

                    <span>
                      Critical
                    </span>

                    <strong>
                      {criticalCount}
                    </strong>

                  </div>

                  <div className="progress-bar">

                    <div
                      className="progress-fill critical-fill"
                      style={{
                        width:
                          totalBugs > 0
                            ? `${(criticalCount / totalBugs) * 100}%`
                            : "0%",
                      }}
                    ></div>

                  </div>

                </div>


                {/* HIGH */}

                <div className="severity-item">

                  <div className="severity-top">

                    <span>
                      High
                    </span>

                    <strong>
                      {highCount}
                    </strong>

                  </div>

                  <div className="progress-bar">

                    <div
                      className="progress-fill high-fill"
                      style={{
                        width:
                          totalBugs > 0
                            ? `${(highCount / totalBugs) * 100}%`
                            : "0%",
                      }}
                    ></div>

                  </div>

                </div>


                {/* MEDIUM */}

                <div className="severity-item">

                  <div className="severity-top">

                    <span>
                      Medium
                    </span>

                    <strong>
                      {mediumCount}
                    </strong>

                  </div>

                  <div className="progress-bar">

                    <div
                      className="progress-fill medium-fill"
                      style={{
                        width:
                          totalBugs > 0
                            ? `${(mediumCount / totalBugs) * 100}%`
                            : "0%",
                      }}
                    ></div>

                  </div>

                </div>


                {/* LOW */}

                <div className="severity-item">

                  <div className="severity-top">

                    <span>
                      Low
                    </span>

                    <strong>
                      {lowCount}
                    </strong>

                  </div>

                  <div className="progress-bar">

                    <div
                      className="progress-fill low-fill"
                      style={{
                        width:
                          totalBugs > 0
                            ? `${(lowCount / totalBugs) * 100}%`
                            : "0%",
                      }}
                    ></div>

                  </div>

                </div>

              </div>

            </div>


            {/* =================================================
                ANALYSIS SUMMARY
                ================================================= */}

            <div className="dashboard-card summary-card">

              <div className="card-header">

                <div>

                  <h2>
                    Analysis Summary
                  </h2>

                  <p>
                    Your current activity
                  </p>

                </div>

                <div className="card-icon">
                  🧠
                </div>

              </div>


              <div className="summary-content">

                <div className="summary-number">
                  {totalAnalyses}
                </div>

                <p>
                  Total code analyses performed
                </p>

                <div className="summary-divider"></div>


                <div className="summary-row">

                  <span>
                    Analyses with bugs
                  </span>

                  <strong>
                    {totalBugs}
                  </strong>

                </div>


                <div className="summary-row">

                  <span>
                    Critical issues
                  </span>

                  <strong>
                    {criticalCount}
                  </strong>

                </div>


                <div className="summary-row">

                  <span>
                    High issues
                  </span>

                  <strong>
                    {highCount}
                  </strong>

                </div>

              </div>

            </div>

          </div>


          {/* =================================================
              ACTION CARDS
              ================================================= */}

          <div className="dashboard-actions">

            <div className="action-card">

              <div className="action-icon">
                🔍
              </div>

              <div className="action-content">

                <h3>
                  Analyze New Code
                </h3>

                <p>
                  Find bugs and get AI-powered
                  fixes for your code.
                </p>

              </div>

              <Link
                to="/analyzer"
                className="action-button primary-action"
              >
                Analyze Code →
              </Link>

            </div>


            <div className="action-card">

              <div className="action-icon">
                📚
              </div>

              <div className="action-content">

                <h3>
                  View Full History
                </h3>

                <p>
                  Review all your previous code
                  analyses and fixes.
                </p>

              </div>

              <Link
                to="/history"
                className="action-button secondary-action"
              >
                View History →
              </Link>

            </div>

          </div>


          {/* =================================================
              RECENT ANALYSES
              ================================================= */}

          <div className="recent-section">

            <div className="section-heading">

              <div>

                <h2>
                  Recent Analyses
                </h2>

                <p>
                  Your latest code analysis activity
                </p>

              </div>

              <span>
                {history.length} total
              </span>

            </div>


            {history.length === 0 ? (

              <div className="empty-dashboard">

                <div className="empty-icon">
                  📂
                </div>

                <h3>
                  No analyses yet
                </h3>

                <p>
                  Analyze your first piece of code
                  to see your activity here.
                </p>

              </div>

            ) : (

              <div className="recent-table">

                <div className="table-header">

                  <span>
                    Language
                  </span>

                  <span>
                    Severity
                  </span>

                  <span>
                    Date
                  </span>

                </div>


                {history
                  .slice(0, 5)
                  .map((item, index) => {

                    const severity =
                      getSeverity(item);

                    return (
                      <div
                        className="table-row"
                        key={
                          item.id ||
                          item.analysis_id ||
                          index
                        }
                      >

                        <span className="language-cell">

                          💻{" "}

                          {item.language ||
                            "Python"}

                        </span>


                        <span>

                          <span
                            className={`severity-badge ${severity.toLowerCase()}`}
                          >
                            {severity}
                          </span>

                        </span>


                        <span className="date-cell">

                          {formatDate(
                            item.created_at ||
                            item.createdAt ||
                            item.date
                          )}

                        </span>

                      </div>
                    );
                  })}

              </div>

            )}

          </div>

        </>
      )}

    </div>
  );
}

export default Dashboard;
