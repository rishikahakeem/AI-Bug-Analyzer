/* eslint-disable no-useless-assignment */
/* eslint-disable no-unused-vars */
import { useState } from "react";

import {
  FaBug,
  FaCode,
  FaSearch,
  FaLightbulb,
  FaCopy,
  FaCheckCircle,
  FaRobot,
  FaExclamationTriangle,
  FaWrench,
  FaBullseye,
  FaUpload,
  FaDownload,
} from "react-icons/fa";

import { analyzeCode } from "../services/api";
import { jsPDF } from "jspdf";

import "./Analyzer.css";


// =========================================================
// PARSE AI RESULT
// =========================================================

const parseAIResult = (text) => {
  const emptyResult = {
    staticAnalysis: "",
    bug: "",
    severity: "NONE",
    explanation: "",
    rootCause: "",
    suggestedFix: "",
    correctedCode: "",
    improvements: "",
  };

  if (!text) {
    return emptyResult;
  }

  const sourceText = String(text).trim();

  const extractSection = (
    sectionName,
    nextSections = []
  ) => {
    const escapedName = sectionName.replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&"
    );

    const nextPattern =
      nextSections.length > 0
        ? nextSections
            .map((section) =>
              section.replace(
                /[.*+?^${}()|[\]\\]/g,
                "\\$&"
              )
            )
            .join("|")
        : "";

    let pattern;

    if (nextPattern) {
      pattern = new RegExp(
        `${escapedName}\\s*:\\s*([\\s\\S]*?)(?=\\n\\s*(?:${nextPattern})\\s*:|$)`,
        "i"
      );
    } else {
      pattern = new RegExp(
        `${escapedName}\\s*:\\s*([\\s\\S]*)`,
        "i"
      );
    }

    const match = sourceText.match(pattern);

    return match
      ? match[1].trim()
      : "";
  };

  const allSections = [
    "BUG DETECTED",
    "SEVERITY",
    "EXPLANATION",
    "ROOT CAUSE",
    "SUGGESTED FIX",
    "CORRECTED CODE",
    "IMPROVEMENTS",
    "STATIC ANALYSIS",
  ];

  let aiText = sourceText;

  // -------------------------------------------------------
  // Support older response format containing
  // "AI ANALYSIS:"
  // -------------------------------------------------------

  const aiAnalysisMatch = sourceText.match(
    /AI ANALYSIS\s*:\s*([\s\S]*)/i
  );

  if (aiAnalysisMatch) {
    aiText = aiAnalysisMatch[1].trim();
  }

  // -------------------------------------------------------
  // Extract each section
  // -------------------------------------------------------

  const bug = extractSection(
    "BUG DETECTED",
    allSections.filter(
      (section) =>
        section !== "BUG DETECTED"
    )
  );

  const severity = extractSection(
    "SEVERITY",
    allSections.filter(
      (section) =>
        section !== "SEVERITY"
    )
  );

  const explanation = extractSection(
    "EXPLANATION",
    allSections.filter(
      (section) =>
        section !== "EXPLANATION"
    )
  );

  const rootCause = extractSection(
    "ROOT CAUSE",
    allSections.filter(
      (section) =>
        section !== "ROOT CAUSE"
    )
  );

  const suggestedFix = extractSection(
    "SUGGESTED FIX",
    allSections.filter(
      (section) =>
        section !== "SUGGESTED FIX"
    )
  );

  let correctedCode = extractSection(
    "CORRECTED CODE",
    allSections.filter(
      (section) =>
        section !== "CORRECTED CODE"
    )
  );

  const improvements = extractSection(
    "IMPROVEMENTS",
    allSections.filter(
      (section) =>
        section !== "IMPROVEMENTS"
    )
  );

  const staticAnalysis = extractSection(
    "STATIC ANALYSIS",
    []
  );

  // -------------------------------------------------------
  // Clean corrected code
  // -------------------------------------------------------

  correctedCode = correctedCode
    .replace(
      /^```[a-zA-Z0-9+#.-]*\s*/i,
      ""
    )
    .replace(
      /\s*```$/i,
      ""
    )
    .trim();

  // -------------------------------------------------------
  // Normalize severity
  // -------------------------------------------------------

  let normalizedSeverity =
    String(severity || "")
      .trim()
      .toUpperCase();

  if (
    normalizedSeverity.includes(
      "CRITICAL"
    )
  ) {
    normalizedSeverity = "CRITICAL";
  } else if (
    normalizedSeverity.includes("HIGH")
  ) {
    normalizedSeverity = "HIGH";
  } else if (
    normalizedSeverity.includes("MEDIUM")
  ) {
    normalizedSeverity = "MEDIUM";
  } else if (
    normalizedSeverity.includes("LOW")
  ) {
    normalizedSeverity = "LOW";
  } else {
    normalizedSeverity = "NONE";
  }

  // -------------------------------------------------------
  // Return parsed result
  // -------------------------------------------------------

  return {
    staticAnalysis,
    bug:
      bug || "No bug detected.",
    severity:
      normalizedSeverity,
    explanation,
    rootCause,
    suggestedFix,
    correctedCode,
    improvements,
  };
};


// =========================================================
// FILE EXTENSION → LANGUAGE
// =========================================================

const getLanguageFromFile = (
  fileName
) => {
  const extension = fileName
    .split(".")
    .pop()
    .toLowerCase();

  const languageMap = {
    py: "Python",
    js: "JavaScript",
    java: "Java",
    c: "C",
    cpp: "C++",
    h: "C",
    hpp: "C++",
    html: "HTML",
    htm: "HTML",
    css: "CSS",
  };

  return (
    languageMap[extension] ||
    null
  );
};



// =========================================================
// CODE QUALITY SCORE
// =========================================================

const getCodeQuality = (analysisResult) => {
  let score = 100;

  const severity = String(
    analysisResult?.severity || "NONE"
  ).toUpperCase();

  const severityPenalty = {
    CRITICAL: 30,
    HIGH: 20,
    MEDIUM: 12,
    LOW: 5,
    NONE: 0,
  };

  score -= severityPenalty[severity] || 0;

  const staticText = String(
    analysisResult?.staticAnalysis || ""
  ).trim();

  if (
    staticText &&
    !staticText.toLowerCase().includes("no static analysis")
  ) {
    const issueLines = staticText
      .split("\\n")
      .filter((line) => line.trim()).length;

    score -= Math.min(issueLines * 4, 20);
  }

  score = Math.max(0, Math.min(100, score));

  const readability = Math.max(
    0,
    Math.min(
      100,
      score + (severity === "HIGH" ? 5 : 0)
    )
  );

  const codeStructure = score;

  const errorHandling = Math.max(
    0,
    Math.min(
      100,
      score -
        (severity === "HIGH" ||
        severity === "CRITICAL"
          ? 5
          : 0)
    )
  );

  const maintainability = Math.max(
    0,
    Math.min(100, score + 3)
  );

  return {
    score,
    readability,
    codeStructure,
    errorHandling,
    maintainability,
  };
};


// =========================================================
// SECURITY ANALYSIS
// =========================================================

const getSecurityAnalysis = (sourceCode, language) => {
  const codeText = String(sourceCode || "");
  const lowerCode = codeText.toLowerCase();

  const issues = [];
  const recommendations = [];

  const addIssue = (title, details, severity) => {
    if (
      !issues.some(
        (issue) => issue.title === title
      )
    ) {
      issues.push({
        title,
        details,
        severity,
      });
    }
  };

  const hasHardcodedSecret =
    /(password|passwd|pwd|api[_-]?key|secret|token|access[_-]?key)\s*[:=]\s*["'][^"']+["']/i.test(
      codeText
    );

  if (hasHardcodedSecret) {
    addIssue(
      "Hardcoded credential detected",
      "A password, API key, secret, token or similar credential appears to be stored directly in the source code.",
      "HIGH"
    );

    recommendations.push(
      "Move credentials to environment variables or a secure secrets manager."
    );
  }

  if (
    /\beval\s*\(/i.test(codeText) ||
    /\bexec\s*\(/i.test(codeText)
  ) {
    addIssue(
      "Dynamic code execution detected",
      "eval() or exec() can execute dynamically supplied code and may create a code-injection risk when input is not trusted.",
      "HIGH"
    );

    recommendations.push(
      "Avoid eval() and exec() with untrusted input; use safer, explicit operations instead."
    );
  }

  if (
    /\bos\.system\s*\(/i.test(codeText) ||
    /subprocess\.(run|call|popen)\s*\(/i.test(codeText) &&
      /shell\s*=\s*true/i.test(codeText)
  ) {
    addIssue(
      "Potential command injection risk",
      "Operating-system commands are executed directly. Risk increases when command arguments contain user-controlled input.",
      "HIGH"
    );

    recommendations.push(
      "Prefer argument arrays over shell commands and validate all external input."
    );
  }

  if (
    /innerhtml\s*=/i.test(codeText) ||
    /dangerouslysetinnerhtml/i.test(codeText)
  ) {
    addIssue(
      "Potential XSS risk",
      "HTML is being inserted directly into a page, which can become a cross-site scripting risk when the content is not sanitized.",
      "MEDIUM"
    );

    recommendations.push(
      "Sanitize untrusted HTML and prefer safe text rendering where possible."
    );
  }

  if (
    /(select|insert|update|delete)[\s\S]{0,100}(\+|f["']|f'|format\s*\()/i.test(
      codeText
    )
  ) {
    addIssue(
      "Potential SQL injection risk",
      "SQL appears to be constructed using string concatenation or interpolation. This can be unsafe when values come from users.",
      "HIGH"
    );

    recommendations.push(
      "Use parameterized queries or prepared statements instead of building SQL with strings."
    );
  }

  if (
    /http:\/\//i.test(codeText)
  ) {
    addIssue(
      "Unencrypted HTTP connection detected",
      "The code contains an HTTP URL rather than HTTPS, which may expose data during transmission.",
      "MEDIUM"
    );

    recommendations.push(
      "Use HTTPS for network communication, especially when transmitting credentials or personal data."
    );
  }

  if (
    /pickle\.loads?\s*\(/i.test(codeText)
  ) {
    addIssue(
      "Unsafe deserialization pattern detected",
      "Python pickle deserialization can execute malicious payloads when the serialized data is untrusted.",
      "HIGH"
    );

    recommendations.push(
      "Do not deserialize untrusted pickle data; use a safer data format such as JSON."
    );
  }

  if (
    /verify\s*=\s*false/i.test(codeText)
  ) {
    addIssue(
      "TLS certificate verification disabled",
      "Disabling certificate verification weakens HTTPS connection security.",
      "MEDIUM"
    );

    recommendations.push(
      "Keep TLS certificate verification enabled in production."
    );
  }

  if (
    /chmod\s*\(\s*[^,]+,\s*0?777/i.test(codeText) ||
    /chmod\s+777/i.test(codeText)
  ) {
    addIssue(
      "Overly permissive file permissions",
      "Permission mode 777 can allow unauthorized users to read, modify or execute files.",
      "MEDIUM"
    );

    recommendations.push(
      "Use the minimum file permissions required by the application."
    );
  }

  const riskOrder = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
    NONE: 0,
  };

  let riskLevel = "LOW";

  if (issues.length === 0) {
    riskLevel = "LOW";
    recommendations.push(
      "No common security-risk patterns were detected by the local security scanner."
    );
  } else {
    riskLevel = issues.reduce(
      (highest, issue) =>
        riskOrder[issue.severity] >
        riskOrder[highest]
          ? issue.severity
          : highest,
      "LOW"
    );
  }

  return {
    riskLevel,
    issues,
    recommendations,
    language,
  };
};


// =========================================================
// ANALYZER COMPONENT
// =========================================================


function Analyzer() {
  const [code, setCode] =
    useState("");

  const [language, setLanguage] =
    useState("Python");

  const [result, setResult] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [copied, setCopied] =
    useState(false);

  const [copiedCode, setCopiedCode] =
    useState(false);

  const [fileName, setFileName] =
    useState("");


  // =======================================================
  // FILE UPLOAD
  // =======================================================

  const handleFileUpload = (
    event
  ) => {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    const detectedLanguage =
      getLanguageFromFile(
        file.name
      );

    if (!detectedLanguage) {
      setError(
        "Unsupported file type. Please upload .py, .js, .java, .c, .cpp, .html, or .css files."
      );

      event.target.value = "";

      return;
    }

    // Backend maximum
    // 15,000 characters
    if (file.size > 15000) {
      setError(
        "File is too large. Please upload a file below 15,000 characters."
      );

      event.target.value = "";

      return;
    }

    const reader =
      new FileReader();

    reader.onload = (e) => {
      const fileContent =
        e.target.result;

      if (
        typeof fileContent !==
        "string"
      ) {
        setError(
          "Unable to read the selected file."
        );

        return;
      }

      setCode(fileContent);

      setLanguage(
        detectedLanguage
      );

      setFileName(
        file.name
      );

      setResult(null);

      setError("");

      setCopied(false);

      setCopiedCode(false);
    };

    reader.onerror = () => {
      setError(
        "Unable to read the selected file."
      );
    };

    reader.readAsText(file);

    // Allow selecting the
    // same file again later
    event.target.value = "";
  };


  // =======================================================
  // ANALYZE CODE
  // =======================================================

  const handleAnalyze =
    async () => {
      if (!code.trim()) {
        setError(
          "Please enter some code to analyze."
        );

        return;
      }

      if (code.length > 15000) {
        setError(
          "Code is too large. Please keep the code below 15,000 characters."
        );

        return;
      }

      setLoading(true);

      setError("");

      setResult(null);

      setCopied(false);

      setCopiedCode(false);

      try {
        const data =
          await analyzeCode(
            code,
            language
          );

        console.log(
          "Analyzer API response:",
          data
        );

        if (data.success) {
          // ------------------------------------------------
          // Preferred structured backend response
          // ------------------------------------------------

          if (data.analysis) {
            const parsedResult = {
              staticAnalysis:
                data.analysis
                  .static_analysis ||
                "",

              bug:
                data.analysis.bug ||
                "",

              severity:
                data.analysis
                  .severity ||
                "NONE",

              explanation:
                data.analysis
                  .explanation ||
                "",

              rootCause:
                data.analysis
                  .root_cause ||
                "",

              suggestedFix:
                data.analysis
                  .suggested_fix ||
                "",

              correctedCode:
                data.analysis
                  .corrected_code ||
                "",

              improvements:
                data.analysis
                  .improvements ||
                "",
            };

            setResult(
              parsedResult
            );
          } else {
            // ------------------------------------------------
            // Fallback for older backend response
            // ------------------------------------------------

            setResult(
              parseAIResult(
                data.result
              )
            );
          }
        } else {
          setError(
            data.message ||
              "Something went wrong while analyzing the code."
          );
        }
      } catch (err) {
        console.error(
          "Analysis error:",
          err
        );

        setError(
          err.response?.data
            ?.message ||
            err.message ||
            "Unable to analyze code."
        );
      } finally {
        setLoading(false);
      }
    };


  // =======================================================
  // CLEAR CODE
  // =======================================================

  const handleClear = () => {
    setCode("");

    setResult(null);

    setError("");

    setCopied(false);

    setCopiedCode(false);

    setFileName("");
  };


  // =======================================================
  // COPY COMPLETE RESULT
  // =======================================================

  const copyResult = async () => {
    if (!result) return;

    const text = `
AI SOFTWARE BUG ANALYZER
========================

Programming Language:
${language}

${fileName ? `Uploaded File:
${fileName}

` : ""}
BUG DETECTED:
${result.bug || "No bug detected."}

SEVERITY:
${result.severity || "NONE"}

EXPLANATION:
${result.explanation || "No explanation available."}

ROOT CAUSE:
${result.rootCause || "No root cause information available."}

SUGGESTED FIX:
${result.suggestedFix || "No suggested fix available."}

CORRECTED CODE:
${result.correctedCode || "No corrected code available."}

IMPROVEMENTS:
${result.improvements || "None"}

CODE QUALITY SCORE:
Overall: ${quality.score}/100
Readability: ${quality.readability}/100
Code Structure: ${quality.codeStructure}/100
Error Handling: ${quality.errorHandling}/100
Maintainability: ${quality.maintainability}/100

SECURITY ANALYSIS:
Risk Level: ${security.riskLevel}
${security.issues.length > 0 ? security.issues.map((issue, index) => `${index + 1}. ${issue.title} [${issue.severity}]
${issue.details}`).join("\n\n") : "No common security-risk patterns detected."}

SECURITY RECOMMENDATIONS:
${security.recommendations.map((item, index) => `${index + 1}. ${item}`).join("\n")}

STATIC ANALYSIS:
${result.staticAnalysis || "No static analysis issues detected."}

========================
Analysis completed successfully
`.trim();

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  };


  // =======================================================
  // COPY CORRECTED CODE
  // =======================================================

  const copyCorrectedCode =
    async () => {
      if (
        !result?.correctedCode
      ) {
        return;
      }

      try {
        await navigator.clipboard.writeText(
          result.correctedCode
        );

        setCopiedCode(true);

        setTimeout(() => {
          setCopiedCode(false);
        }, 2000);
      } catch (err) {
        console.error(
          "Copy corrected code failed:",
          err
        );
      }
    };


  // =======================================================
  // DOWNLOAD COMPLETE TXT REPORT
  // =======================================================

  const downloadReport = () => {
    if (!result) return;

    const reportText = `
AI SOFTWARE BUG ANALYZER
========================

Programming Language:
${language}

${fileName ? `Uploaded File:
${fileName}

` : ""}
BUG DETECTED:
${result.bug || "No bug detected."}

SEVERITY:
${result.severity || "NONE"}

EXPLANATION:
${result.explanation || "No explanation available."}

ROOT CAUSE:
${result.rootCause || "No root cause information available."}

SUGGESTED FIX:
${result.suggestedFix || "No suggested fix available."}

CORRECTED CODE:
${result.correctedCode || "No corrected code available."}

IMPROVEMENTS:
${result.improvements || "None"}

CODE QUALITY SCORE:
Overall: ${quality.score}/100
Readability: ${quality.readability}/100
Code Structure: ${quality.codeStructure}/100
Error Handling: ${quality.errorHandling}/100
Maintainability: ${quality.maintainability}/100

SECURITY ANALYSIS:
Risk Level: ${security.riskLevel}

${security.issues.length > 0 ? security.issues.map((issue, index) => `${index + 1}. ${issue.title} [${issue.severity}]
${issue.details}`).join("\n\n") : "No common security-risk patterns detected."}

SECURITY RECOMMENDATIONS:
${security.recommendations.map((item, index) => `${index + 1}. ${item}`).join("\n")}

STATIC ANALYSIS:
${result.staticAnalysis || "No static analysis issues detected."}

========================
Analysis completed successfully
`.trim();

    try {
      const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const safeLanguage = language.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      link.download = `bug-analysis-${safeLanguage}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download report failed:", err);
      setError("Unable to download the analysis report.");
    }
  };


  // =======================================================
  // SEVERITY CLASS
  // =======================================================

  const getSeverityClass =
    () => {
      if (!result?.severity) {
        return "";
      }

      return result.severity
        .toLowerCase()
        .replace(
          /\s+/g,
          "-"
        );
    };


  const quality = getCodeQuality(result);
  const security = getSecurityAnalysis(code, language);


  // =======================================================
  // DOWNLOAD PDF REPORT
  // =======================================================

  const downloadPDFReport = () => {
    if (!result) {
      return;
    }

    try {
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      const margin = 15;
      const maxWidth = pageWidth - margin * 2;
      let y = 18;

      const addText = (
        text,
        options = {}
      ) => {
        const {
          size = 10,
          bold = false,
          gap = 6,
        } = options;

        doc.setFontSize(size);
        doc.setFont(
          "helvetica",
          bold ? "bold" : "normal"
        );

        const lines = doc.splitTextToSize(
          String(text || ""),
          maxWidth
        );

        const lineHeight = size * 0.45 + 1;

        if (y + lines.length * lineHeight > 280) {
          doc.addPage();
          y = 18;
        }

        doc.text(lines, margin, y);
        y += lines.length * lineHeight + gap;
      };

      addText(
        "AI SOFTWARE BUG ANALYZER",
        { size: 16, bold: true, gap: 8 }
      );

      addText(`Programming Language: ${language}`, {
        bold: true,
      });

      if (fileName) {
        addText(`Uploaded File: ${fileName}`);
      }

      addText("BUG DETECTED", {
        size: 12,
        bold: true,
      });
      addText(
        result.bug || "No bug detected."
      );

      addText("SEVERITY", {
        size: 12,
        bold: true,
      });
      addText(result.severity || "NONE");

      addText("CODE QUALITY SCORE", {
        size: 12,
        bold: true,
      });
      addText(
        `Overall: ${quality.score}/100 | Readability: ${quality.readability}/100 | Code Structure: ${quality.codeStructure}/100 | Error Handling: ${quality.errorHandling}/100 | Maintainability: ${quality.maintainability}/100`
      );

      addText("SECURITY ANALYSIS", {
        size: 12,
        bold: true,
      });
      addText(`Risk Level: ${security.riskLevel}`);

      if (security.issues.length > 0) {
        security.issues.forEach((issue, index) => {
          addText(
            `${index + 1}. ${issue.title} [${issue.severity}]`
          );
          addText(issue.details);
        });
      } else {
        addText("No common security-risk patterns detected.");
      }

      addText("SECURITY RECOMMENDATIONS", {
        size: 12,
        bold: true,
      });
      security.recommendations.forEach((item, index) => {
        addText(`${index + 1}. ${item}`);
      });

      addText("EXPLANATION", {
        size: 12,
        bold: true,
      });
      addText(
        result.explanation ||
          "No explanation available."
      );

      addText("ROOT CAUSE", {
        size: 12,
        bold: true,
      });
      addText(
        result.rootCause ||
          "No root cause information available."
      );

      addText("SUGGESTED FIX", {
        size: 12,
        bold: true,
      });
      addText(
        result.suggestedFix ||
          "No suggested fix available."
      );

      addText("CORRECTED CODE", {
        size: 12,
        bold: true,
      });
      addText(
        result.correctedCode ||
          "No corrected code available."
      );

      addText("IMPROVEMENTS", {
        size: 12,
        bold: true,
      });
      addText(result.improvements || "None");

      addText("STATIC ANALYSIS", {
        size: 12,
        bold: true,
      });
      addText(
        result.staticAnalysis ||
          "No static analysis issues detected."
      );

      addText("Analysis completed successfully", {
        bold: true,
        gap: 2,
      });

      const safeLanguage = language
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-");

      doc.save(
        `bug-analysis-${safeLanguage}.pdf`
      );
    } catch (err) {
      console.error(
        "PDF download failed:",
        err
      );

      setError(
        "Unable to download the PDF report."
      );
    }
  };


  // =======================================================
  // UI
  // =======================================================

  return (
    <div className="analyzer-page">

      {/* ===================================================
          HEADER
          =================================================== */}

      <div className="analyzer-header">

        <div className="analyzer-title">

          <div className="title-icon">
            <FaRobot />
          </div>

          <div>

            <h1>
              AI Software Bug Analyzer
            </h1>

            <p>
              Analyze your code, detect bugs,
              understand the root cause and
              get a corrected solution.
            </p>

          </div>

        </div>

      </div>


      {/* ===================================================
          MAIN CONTENT
          =================================================== */}

      <div className="analyzer-container">


        {/* =================================================
            CODE INPUT CARD
            ================================================= */}

        <div className="analyzer-card">


          {/* CARD HEADER */}

          <div className="card-header">

            <div className="card-heading">

              <FaCode />

              <div>

                <h2>
                  Code Analyzer
                </h2>

                <p>
                  Enter your source code below
                  and let AI analyze it.
                </p>

              </div>

            </div>

          </div>


          {/* =================================================
              LANGUAGE
              ================================================= */}

          <div className="language-section">

            <label htmlFor="language">
              Programming Language
            </label>

            <select
              id="language"
              value={language}
              onChange={(e) => {
                setLanguage(
                  e.target.value
                );

                setFileName("");
              }}
            >

              <option value="Python">
                Python
              </option>

              <option value="JavaScript">
                JavaScript
              </option>

              <option value="Java">
                Java
              </option>

              <option value="C">
                C
              </option>

              <option value="C++">
                C++
              </option>

              <option value="HTML">
                HTML
              </option>

              <option value="CSS">
                CSS
              </option>

            </select>

          </div>


          {/* =================================================
              FILE UPLOAD
              ================================================= */}

          <div className="file-upload-section">

            <label
              htmlFor="code-file"
              className="file-upload-btn"
            >

              <FaUpload />

              Upload Code File

            </label>

            <input
              id="code-file"
              type="file"
              accept=".py,.js,.java,.c,.cpp,.h,.hpp,.html,.htm,.css"
              onChange={
                handleFileUpload
              }
              hidden
            />

            {fileName && (
              <span className="uploaded-file-name">
                📄 {fileName}
              </span>
            )}

            <small>
              Supported: .py, .js, .java,
              .c, .cpp, .html, .css
            </small>

          </div>


          {/* =================================================
              CODE EDITOR
              ================================================= */}

          <div className="code-editor-section">

            <div className="editor-label">

              <span>
                Your Code
              </span>

              <span className="language-badge">
                {language}
              </span>

            </div>

            <textarea
              className="code-editor"
              value={code}
              onChange={(e) => {
                setCode(
                  e.target.value
                );

                setFileName("");
              }}
              placeholder={`Enter your ${language} code here...`}
              spellCheck="false"
            />

          </div>


          {/* =================================================
              BUTTONS
              ================================================= */}

          <div className="analyzer-actions">

            <button
              className="analyze-btn"
              onClick={
                handleAnalyze
              }
              disabled={loading}
            >

              {loading ? (
                <>
                  <span className="loading-spinner"></span>

                  Analyzing...
                </>
              ) : (
                <>
                  <FaSearch />

                  Analyze Code
                </>
              )}

            </button>


            <button
              className="clear-btn"
              onClick={
                handleClear
              }
              disabled={loading}
            >
              Clear
            </button>

          </div>


          {/* =================================================
              ERROR
              ================================================= */}

          {error && (
            <div className="analyzer-error">

              <FaExclamationTriangle />

              <span>
                {error}
              </span>

            </div>
          )}

        </div>


        {/* =================================================
            ANALYSIS RESULT
            ================================================= */}

        {result && (

          <div className="analysis-result">


            {/* =================================================
                RESULT HEADER
                ================================================= */}

            <div className="result-header">

              <div>

                <div className="result-title">

                  <FaRobot />

                  <h2>
                    AI Analysis Report
                  </h2>

                </div>

                <p>
                  Detailed analysis of your
                  submitted code.
                </p>

              </div>


              {/* RESULT HEADER BUTTONS */}

              <div className="result-header-actions">


                {/* COPY REPORT */}

                <button
                  className="copy-result-btn"
                  onClick={copyResult}
                >

                  {copied ? (
                    <>
                      <FaCheckCircle />
                      Copied
                    </>
                  ) : (
                    <>
                      <FaCopy />
                      Copy Report
                    </>
                  )}

                </button>


                {/* DOWNLOAD REPORT */}

                <button
                  className="download-result-btn"
                  onClick={
                    downloadReport
                  }
                >

                  <FaDownload />

                  Download TXT

                </button>

                <button
                  className="download-result-btn"
                  onClick={downloadPDFReport}
                >
                  <FaDownload />
                  Download PDF
                </button>

              </div>

            </div>


            {/* =================================================
                BUG DETECTED
                ================================================= */}

            <div className="result-section bug-section">

              <div className="section-title">

                <div className="section-icon bug-icon">
                  <FaBug />
                </div>

                <h3>
                  BUG DETECTED
                </h3>

              </div>

              <div className="section-content">

                <p>
                  {result.bug ||
                    "No bug information was returned."}
                </p>

              </div>

            </div>


            {/* =================================================
                SEVERITY
                ================================================= */}

            <div className="result-section severity-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaExclamationTriangle />

                </div>

                <h3>
                  SEVERITY
                </h3>

              </div>

              <div className="section-content">

                <span
                  className={`severity-badge ${getSeverityClass()}`}
                >
                  {result.severity}
                </span>

              </div>

            </div>


            {/* =================================================
                CODE QUALITY SCORE
                ================================================= */}

            <div className="result-section quality-score-section">

              <div className="section-title">

                <div className="section-icon">
                  <FaCheckCircle />
                </div>

                <h3>
                  CODE QUALITY SCORE
                </h3>

              </div>

              <div className="quality-score-card">

                <div className="quality-score-main">

                  <div className="quality-score-circle">
                    <span className="quality-score-number">
                      {quality.score}
                    </span>

                    <span className="quality-score-out-of">
                      / 100
                    </span>
                  </div>

                  <div className="quality-score-text">

                    <strong>
                      {quality.score >= 80
                        ? "Good Code Quality"
                        : quality.score >= 60
                        ? "Needs Improvement"
                        : "Needs Attention"}
                    </strong>

                    <p>
                      Score based on the detected bugs,
                      severity and static-analysis issues.
                    </p>

                  </div>

                </div>

                <div className="quality-metrics">

                  <div className="quality-metric">
                    <span>Readability</span>
                    <strong>
                      {quality.readability}/100
                    </strong>
                  </div>

                  <div className="quality-metric">
                    <span>Code Structure</span>
                    <strong>
                      {quality.codeStructure}/100
                    </strong>
                  </div>

                  <div className="quality-metric">
                    <span>Error Handling</span>
                    <strong>
                      {quality.errorHandling}/100
                    </strong>
                  </div>

                  <div className="quality-metric">
                    <span>Maintainability</span>
                    <strong>
                      {quality.maintainability}/100
                    </strong>
                  </div>

                </div>

              </div>

            </div>


            {/* =================================================
                SECURITY ANALYSIS
                ================================================= */}

            <div className="result-section security-analysis-section">

              <div className="section-title">

                <div className="section-icon">
                  <FaExclamationTriangle />
                </div>

                <h3>
                  SECURITY ANALYSIS
                </h3>

              </div>

              <div className="security-analysis-card">

                <div className={`security-risk-badge ${security.riskLevel.toLowerCase()}`}>
                  Security Risk: {security.riskLevel}
                </div>

                {security.issues.length > 0 ? (
                  <div className="security-issues">

                    <h4>
                      Security Issues Found
                    </h4>

                    {security.issues.map(
                      (issue, index) => (
                        <div
                          className="security-issue"
                          key={`${issue.title}-${index}`}
                        >

                          <div className="security-issue-header">
                            <strong>
                              {index + 1}. {issue.title}
                            </strong>

                            <span
                              className={`security-severity ${issue.severity.toLowerCase()}`}
                            >
                              {issue.severity}
                            </span>
                          </div>

                          <p>
                            {issue.details}
                          </p>

                        </div>
                      )
                    )}

                  </div>
                ) : (
                  <div className="security-safe-message">
                    <FaCheckCircle />
                    <span>
                      No common security-risk patterns were
                      detected by the local security scanner.
                    </span>
                  </div>
                )}

                <div className="security-recommendations">

                  <h4>
                    Security Recommendations
                  </h4>

                  <ul>
                    {security.recommendations.map(
                      (recommendation, index) => (
                        <li key={index}>
                          {recommendation}
                        </li>
                      )
                    )}
                  </ul>

                </div>

                <p className="security-note">
                  Security analysis checks common code
                  patterns. It is a first-level scanner and
                  does not replace a professional security
                  audit.
                </p>

              </div>

            </div>


            {/* =================================================
                EXPLANATION
                ================================================= */}


            <div className="result-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaLightbulb />

                </div>

                <h3>
                  EXPLANATION
                </h3>

              </div>

              <div className="section-content">

                <p>
                  {result.explanation ||
                    "No explanation available."}
                </p>

              </div>

            </div>


            {/* =================================================
                ROOT CAUSE
                ================================================= */}

            <div className="result-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaBullseye />

                </div>

                <h3>
                  ROOT CAUSE
                </h3>

              </div>

              <div className="section-content">

                <p>
                  {result.rootCause ||
                    "No root cause information available."}
                </p>

              </div>

            </div>


            {/* =================================================
                SUGGESTED FIX
                ================================================= */}

            <div className="result-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaWrench />

                </div>

                <h3>
                  SUGGESTED FIX
                </h3>

              </div>

              <div className="section-content">

                <p>
                  {result.suggestedFix ||
                    "No suggested fix available."}
                </p>

              </div>

            </div>


            {/* =================================================
                CORRECTED CODE
                ================================================= */}

            <div className="result-section corrected-code-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaCode />

                </div>

                <h3>
                  CORRECTED CODE
                </h3>

              </div>


              <div className="corrected-code-wrapper">


                <div className="corrected-code-header">

                  <span>
                    Fixed {language} Code
                  </span>


                  <button
                    className="copy-code-btn"
                    onClick={
                      copyCorrectedCode
                    }
                    disabled={
                      !result.correctedCode
                    }
                  >

                    {copiedCode ? (
                      <>
                        <FaCheckCircle />
                        Copied
                      </>
                    ) : (
                      <>
                        <FaCopy />
                        Copy Code
                      </>
                    )}

                  </button>

                </div>


                <pre className="corrected-code">

                  <code>
                    {result.correctedCode ||
                      "No corrected code available."}
                  </code>

                </pre>

              </div>

            </div>


            {/* =================================================
                IMPROVEMENTS
                ================================================= */}

            <div className="result-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaLightbulb />

                </div>

                <h3>
                  IMPROVEMENTS
                </h3>

              </div>

              <div className="section-content">

                <p className="improvements-text">
                  {result.improvements ||
                    "No additional improvements suggested."}
                </p>

              </div>

            </div>


            {/* =================================================
                STATIC ANALYSIS
                ================================================= */}

            <div className="result-section static-analysis-section">

              <div className="section-title">

                <div className="section-icon">

                  <FaSearch />

                </div>

                <h3>
                  STATIC ANALYSIS
                </h3>

              </div>

              <div className="section-content">

                <pre className="static-analysis">
                  {result.staticAnalysis ||
                    "No static analysis information available."}
                </pre>

              </div>

            </div>


            {/* =================================================
                REPORT FOOTER
                ================================================= */}

            <div className="report-footer">

              <FaCheckCircle />

              <span>
                Analysis completed successfully
              </span>

            </div>

          </div>

        )}

      </div>

    </div>
  );
}


export default Analyzer;