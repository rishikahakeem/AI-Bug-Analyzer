/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  FaHistory,
  FaSearch,
  FaTrash,
  FaCode,
  FaChevronDown,
  FaChevronUp,
  FaBug,
  FaShieldAlt,
  FaClipboardCheck,
  FaExclamationTriangle,
  FaCheckCircle,
} from "react-icons/fa";

import "./History.css";

const API_URL = "http://127.0.0.1:5000";

/* ============================================================
   DATE
   ============================================================ */

const formatDate = (dateValue) => {
  if (!dateValue) {
    return "Unknown date";
  }

  const value = String(dateValue).trim();

  const mysqlMatch = value.match(
    /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/
  );

  if (mysqlMatch) {
    const [
      ,
      year,
      month,
      day,
      hour,
      minute,
      second = "00",
    ] = mysqlMatch;

    const date = new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second)
    );

    if (!isNaN(date.getTime())) {
      return new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }).format(date);
    }
  }

  const parsed = new Date(value);

  if (!isNaN(parsed.getTime())) {
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }).format(parsed);
  }

  return value;
};

/* ============================================================
   CLEAN REPORT
   ============================================================ */

const cleanReport = (result) => {
  if (!result) {
    return "";
  }

  return String(result)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/<[^>]*>/g, "")
    .trim();
};

/* ============================================================
   SECTION NAMES
   ============================================================ */

const SECTION_NAMES = [
  "BUG DETECTED",
  "SEVERITY",
  "EXPLANATION",
  "ROOT CAUSE",
  "SUGGESTED FIX",
  "CORRECTED CODE",
  "IMPROVEMENTS",
  "WARNINGS",
  "SECURITY ANALYSIS",
  "SECURITY RECOMMENDATIONS",
  "ORIGINAL STATIC ANALYSIS",
  "STATIC ANALYSIS",
  "POST-FIX STATIC ANALYSIS",
  "COMPLEXITY ANALYSIS",
  "POST-FIX SECURITY VALIDATION",
];

/* ============================================================
   GET SECTION
   ============================================================ */

const getSection = (result, requestedTitle) => {
  const text = cleanReport(result);

  if (!text) {
    return "";
  }

  const title = requestedTitle
    .replace(/^###\s*/, "")
    .replace(/\*\*/g, "")
    .trim()
    .toUpperCase();

  const escapeRegExp = (value) => {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  };

  const escapedTitle = escapeRegExp(title);

  const startPattern = new RegExp(
    `(?:^|\\n)\\s*(?:###\\s*)?(?:\\*\\*)?${escapedTitle}(?:\\*\\*)?\\s*:?[ \\t]*(?:\\n|$)`,
    "i"
  );

  const startMatch = startPattern.exec(text);

  if (!startMatch) {
    return "";
  }

  const contentStart =
    startMatch.index + startMatch[0].length;

  let nextPosition = text.length;

  SECTION_NAMES.forEach((sectionName) => {
    if (
      sectionName === title ||
      (
        title === "ORIGINAL STATIC ANALYSIS" &&
        sectionName === "STATIC ANALYSIS"
      )
    ) {
      return;
    }

    const escaped = escapeRegExp(sectionName);

    const nextPattern = new RegExp(
      `(?:^|\\n)\\s*(?:###\\s*)?(?:\\*\\*)?${escaped}(?:\\*\\*)?\\s*:?[ \\t]*(?:\\n|$)`,
      "i"
    );

    const remainingText = text.slice(contentStart);

    const nextMatch =
      nextPattern.exec(remainingText);

    if (nextMatch) {
      const position =
        contentStart + nextMatch.index;

      if (position < nextPosition) {
        nextPosition = position;
      }
    }
  });

  const separatorPosition = text.indexOf(
    "\n========================",
    contentStart
  );

  if (
    separatorPosition !== -1 &&
    separatorPosition < nextPosition
  ) {
    nextPosition = separatorPosition;
  }

  return text
    .slice(contentStart, nextPosition)
    .trim();
};

/* ============================================================
   STATIC ANALYSIS
   ============================================================ */

const getStaticAnalysis = (result) => {
  const original = getSection(
    result,
    "ORIGINAL STATIC ANALYSIS"
  );

  if (original) {
    return original;
  }

  const normal = getSection(
    result,
    "STATIC ANALYSIS"
  );

  return (
    normal ||
    "No static analysis issues detected."
  );
};

/* ============================================================
   POST FIX
   ============================================================ */

const getPostFixAnalysis = (result) => {
  return (
    getSection(
      result,
      "POST-FIX STATIC ANALYSIS"
    ) ||
    "No static-analysis issues detected after automatic fixes."
  );
};

/* ============================================================
   SECURITY
   ============================================================ */

const getSecurityAnalysis = (result) => {
  return (
    getSection(
      result,
      "SECURITY ANALYSIS"
    ) ||
    "No security analysis available."
  );
};

/* ============================================================
   SECURITY RECOMMENDATIONS
   ============================================================ */

const getSecurityRecommendations = (result) => {
  return (
    getSection(
      result,
      "SECURITY RECOMMENDATIONS"
    ) ||
    "No security recommendations available."
  );
};

/* ============================================================
   COMPLEXITY
   ============================================================ */

const getComplexityAnalysis = (result) => {
  return (
    getSection(
      result,
      "COMPLEXITY ANALYSIS"
    ) ||
    "No complexity analysis available."
  );
};

/* ============================================================
   POST FIX SECURITY
   ============================================================ */

const getPostFixSecurity = (result) => {
  return (
    getSection(
      result,
      "POST-FIX SECURITY VALIDATION"
    ) ||
    "No post-fix security validation available."
  );
};

/* ============================================================
   SEVERITY
   ============================================================ */

const normalizeSeverity = (severity) => {
  const value = String(
    severity || "NONE"
  )
    .trim()
    .toUpperCase();

  const allowed = [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
    "NONE",
  ];

  return allowed.includes(value)
    ? value
    : "NONE";
};

/* ============================================================
   SEVERITY CLASS
   ============================================================ */

const getSeverityClass = (severity) => {
  switch (severity) {
    case "CRITICAL":
      return "critical";

    case "HIGH":
      return "high";

    case "MEDIUM":
      return "medium";

    case "LOW":
      return "low";

    default:
      return "none";
  }
};

/* ============================================================
   COMPONENT
   ============================================================ */

const HistoryPage = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  const [languageFilter, setLanguageFilter] =
    useState("ALL");

  const [severityFilter, setSeverityFilter] =
    useState("ALL");

  const [expandedId, setExpandedId] =
    useState(null);

  /* ==========================================================
     FETCH
     ========================================================== */

  const fetchHistory = async () => {
    try {
      setLoading(true);

      const userId =
        localStorage.getItem("userId");

      if (!userId) {
        setHistory([]);
        return;
      }

      const response = await axios.get(
        `${API_URL}/api/history/${userId}`
      );

      if (response.data?.success) {
        setHistory(
          response.data.analyses || []
        );
      } else {
        setHistory([]);
      }

    } catch (error) {
      console.error(
        "History error:",
        error.response?.data ||
          error.message
      );

      setHistory([]);

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  /* ==========================================================
     DELETE
     ========================================================== */

  const handleDelete = async (analysisId) => {
    try {
      const response = await axios.delete(
        `${API_URL}/api/history/${analysisId}`
      );

      if (response.data?.success) {

        setHistory((previous) =>
          previous.filter(
            (item) => item.id !== analysisId
          )
        );

        if (expandedId === analysisId) {
          setExpandedId(null);
        }

      } else {
        alert(
          response.data?.message ||
            "Could not delete the analysis."
        );
      }

    } catch (error) {
      console.error(
        "Delete error:",
        error.response?.data ||
          error.message
      );

      alert(
        "Could not delete the analysis."
      );
    }
  };

  /* ==========================================================
     LANGUAGES
     ========================================================== */

  const languages = useMemo(() => {
    const values = history
      .map((item) => item.language)
      .filter(Boolean);

    return [
      "ALL",
      ...new Set(values),
    ];
  }, [history]);

  /* ==========================================================
     FILTER
     ========================================================== */

  const filteredHistory = useMemo(() => {

    return history.filter((item) => {

      const language = String(
        item.language || ""
      );

      const result = String(
        item.result || ""
      );

      const severity = normalizeSeverity(
        getSection(result, "SEVERITY")
      );

      const searchText =
        search.toLowerCase();

      const matchesSearch =
        !searchText ||
        language
          .toLowerCase()
          .includes(searchText) ||
        result
          .toLowerCase()
          .includes(searchText);

      const matchesLanguage =
        languageFilter === "ALL" ||
        language.toLowerCase() ===
          languageFilter.toLowerCase();

      const matchesSeverity =
        severityFilter === "ALL" ||
        severity === severityFilter;

      return (
        matchesSearch &&
        matchesLanguage &&
        matchesSeverity
      );
    });

  }, [
    history,
    search,
    languageFilter,
    severityFilter,
  ]);

  /* ==========================================================
     LOADING
     ========================================================== */

  if (loading) {
    return (
      <div className="history-page">

        <div className="history-loading">

          <FaHistory />

          <p>
            Loading analysis history...
          </p>

        </div>

      </div>
    );
  }

  /* ==========================================================
     PAGE
     ========================================================== */

  return (
    <div className="history-page">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div className="history-header">

        <div className="history-title">

          <div className="history-title-icon">
            <FaHistory />
          </div>

          <div>

            <h1>
              Analysis History
            </h1>

            <p>
              View and manage your
              previous code analyses.
            </p>

          </div>

        </div>

        <div className="history-count">

          {filteredHistory.length} Analysis
          {filteredHistory.length !== 1
            ? "es"
            : ""}

        </div>

      </div>

      {/* ====================================================
          FILTERS
      ==================================================== */}

      <div className="history-filters">

        <div className="history-search">

          <FaSearch />

          <input
            type="text"
            placeholder="Search analyses..."
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
          />

        </div>

        <select
          value={languageFilter}
          onChange={(event) =>
            setLanguageFilter(
              event.target.value
            )
          }
        >

          {languages.map((language) => (

            <option
              key={language}
              value={language}
            >
              {language === "ALL"
                ? "All Languages"
                : language}
            </option>

          ))}

        </select>

        <select
          value={severityFilter}
          onChange={(event) =>
            setSeverityFilter(
              event.target.value
            )
          }
        >

          <option value="ALL">
            All Severity
          </option>

          <option value="CRITICAL">
            Critical
          </option>

          <option value="HIGH">
            High
          </option>

          <option value="MEDIUM">
            Medium
          </option>

          <option value="LOW">
            Low
          </option>

          <option value="NONE">
            None
          </option>

        </select>

      </div>

      {/* ====================================================
          EMPTY
      ==================================================== */}

      {filteredHistory.length === 0 ? (

        <div className="history-empty">

          <FaHistory />

          <h2>
            No analysis history found
          </h2>

          <p>
            {history.length === 0
              ? "Your analyzed code will appear here."
              : "Try changing your search or filters."}
          </p>

        </div>

      ) : (

        <div className="history-list">

          {filteredHistory.map((item) => {

            const result = String(
              item.result || ""
            ).trim();

            const historyDataUnavailable = !result;

            const bugSection =
              getSection(
                result,
                "BUG DETECTED"
              );

            const bug =
              bugSection ||
              (historyDataUnavailable
                ? "Detailed report was not stored for this older analysis."
                : "No major bugs detected.");

            const severitySection =
              getSection(
                result,
                "SEVERITY"
              );

            const severity =
              normalizeSeverity(
                severitySection
              );

            const explanationSection =
              getSection(
                result,
                "EXPLANATION"
              );

            const explanation =
              explanationSection ||
              (historyDataUnavailable
                ? "Run the analysis again to store the full report."
                : "No major explanation was provided.");

            const rootCauseSection =
              getSection(
                result,
                "ROOT CAUSE"
              );

            const rootCause =
              rootCauseSection ||
              (historyDataUnavailable
                ? "No stored report data is available for this history item."
                : "No major root cause was identified.");

            const suggestedFixSection =
              getSection(
                result,
                "SUGGESTED FIX"
              );

            const suggestedFix =
              suggestedFixSection ||
              (historyDataUnavailable
                ? "No stored suggestion is available for this older analysis."
                : "No specific automatic fix was required.");

            const correctedCodeSection =
              getSection(
                result,
                "CORRECTED CODE"
              );

            const correctedCode =
              correctedCodeSection ||
              (historyDataUnavailable
                ? "No stored corrected code is available."
                : "No corrected code was generated.");

            const improvementsSection =
              getSection(
                result,
                "IMPROVEMENTS"
              );

            const improvements =
              improvementsSection ||
              (historyDataUnavailable
                ? "No stored improvement notes are available."
                : "No automatic improvements were required.");

            const warningsSection =
              getSection(
                result,
                "WARNINGS"
              );

            const warnings =
              warningsSection ||
              (historyDataUnavailable
                ? "No stored warnings are available."
                : "No static-analysis warnings detected.");

            const security =
              getSecurityAnalysis(result);

            const securityRecommendations =
              getSecurityRecommendations(result);

            const complexityAnalysis =
              getComplexityAnalysis(result);

            const postFixSecurity =
              getPostFixSecurity(result);

            const staticAnalysis =
              getStaticAnalysis(result);

            const postFixAnalysis =
              getPostFixAnalysis(result);

            const isExpanded =
              expandedId === item.id;

            return (

              <div
                className="history-card"
                key={item.id}
              >

                {/* =================================================
                    CARD HEADER
                ================================================= */}

                <div className="history-card-header">

                  <div className="history-card-main">

                    <div className="history-language-icon">
                      <FaCode />
                    </div>

                    <div>

                      <h2>
                        {item.language ||
                          "Unknown"} Analysis
                      </h2>

                      <p>
                        {formatDate(
                          item.created_at
                        )}
                      </p>

                    </div>

                  </div>

                  <div className="history-card-actions">

                    <span
                      className={`severity-badge ${getSeverityClass(
                        severity
                      )}`}
                    >
                      {severity}
                    </span>

                    <button
                      type="button"
                      className="history-toggle-btn"
                      onClick={() =>
                        setExpandedId(
                          isExpanded
                            ? null
                            : item.id
                        )
                      }
                    >

                      {isExpanded ? (

                        <>
                          <FaChevronUp />
                          Hide Details
                        </>

                      ) : (

                        <>
                          <FaChevronDown />
                          Show Details
                        </>

                      )}

                    </button>

                    <button
                      type="button"
                      className="history-delete-btn"
                      onClick={() =>
                        handleDelete(
                          item.id
                        )
                      }
                    >

                      <FaTrash />
                      Delete

                    </button>

                  </div>

                </div>

                {/* =================================================
                    DETAILS
                ================================================= */}

                {isExpanded && (

                  <div className="history-details">

                    <section className="history-section">

                      <h3 className="section-code">

                        <FaCode />

                        Analyzed Code

                      </h3>

                      <pre className="code-block">

                        {item.code ||
                          "No submitted code available."}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-bug">

                        <FaBug />

                        BUG DETECTED

                      </h3>

                      <div className="text-block">

                        {bug}

                      </div>

                    </section>

                    <section className="history-section">

                      <h3 className="section-severity">

                        <FaExclamationTriangle />

                        SEVERITY

                      </h3>

                      <span
                        className={`severity-large ${getSeverityClass(
                          severity
                        )}`}
                      >
                        {severity}
                      </span>

                    </section>

                    <section className="history-section">

                      <h3 className="section-explanation">

                        <FaClipboardCheck />

                        EXPLANATION

                      </h3>

                      <div className="text-block">

                        {explanation}

                      </div>

                    </section>

                    <section className="history-section">

                      <h3 className="section-root">

                        <FaBug />

                        ROOT CAUSE

                      </h3>

                      <div className="text-block">

                        {rootCause}

                      </div>

                    </section>

                    <section className="history-section">

                      <h3 className="section-fix">

                        <FaCheckCircle />

                        SUGGESTED FIX

                      </h3>

                      <div className="text-block">

                        {suggestedFix}

                      </div>

                    </section>

                    <section className="history-section">

                      <h3 className="section-corrected">

                        <FaCheckCircle />

                        CORRECTED CODE

                      </h3>

                      <pre className="code-block">

                        {correctedCode}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-improvements">

                        <FaCheckCircle />

                        IMPROVEMENTS

                      </h3>

                      <div className="text-block">

                        {improvements}

                      </div>

                    </section>

                    <section className="history-section">

                      <h3 className="section-warning">

                        <FaExclamationTriangle />

                        WARNINGS

                      </h3>

                      <pre className="analysis-block">

                        {warnings}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-security">

                        <FaShieldAlt />

                        SECURITY ANALYSIS

                      </h3>

                      <pre className="analysis-block">

                        {security}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-security">

                        <FaShieldAlt />

                        SECURITY RECOMMENDATIONS

                      </h3>

                      <pre className="analysis-block">

                        {securityRecommendations}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-complexity">

                        <FaClipboardCheck />

                        COMPLEXITY ANALYSIS

                      </h3>

                      <pre className="analysis-block">

                        {complexityAnalysis}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-static">

                        <FaClipboardCheck />

                        STATIC ANALYSIS

                      </h3>

                      <pre className="analysis-block">

                        {staticAnalysis}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-security">

                        <FaShieldAlt />

                        POST-FIX SECURITY VALIDATION

                      </h3>

                      <pre className="analysis-block">

                        {postFixSecurity}

                      </pre>

                    </section>

                    <section className="history-section">

                      <h3 className="section-static">

                        <FaClipboardCheck />

                        POST-FIX STATIC ANALYSIS

                      </h3>

                      <pre className="analysis-block">

                        {postFixAnalysis}

                      </pre>

                    </section>

                    <div className="analysis-completed">

                      <div className="completed-line">
                        ========================
                      </div>

                      <div>
                        Analysis completed successfully
                      </div>

                    </div>

                  </div>

                )}

              </div>

            );

          })}

        </div>

      )}

    </div>
  );
};

export default HistoryPage;