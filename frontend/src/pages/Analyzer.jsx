// BUILD MARKER v7
//* eslint-disable no-useless-assignment */

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

import { jsPDF } from "jspdf";

import { analyzeCode } from "../services/api";

import GitHubImport from "../components/GitHubImport";

import "./Analyzer.css";


/* =========================================================
   HELPER FUNCTIONS
========================================================= */

const cleanTextValue = (value = "") => {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return "";
  return String(value).replace(/\r/g, "").replace(/[ \t]+\n/g, "\n").replace(/\.\.+$/g, ".").trim();
};

const cleanSentence = (value = "") => {
  if (value === null || value === undefined || typeof value === "object") return "";
  const text = cleanTextValue(value);
  if (!text) return "";
  return text.replace(/\.\.+$/g, ".").replace(/,+$/g, "").trim();
};


/* =========================================================
   STATIC ANALYSIS NORMALIZATION
========================================================= */

const normalizeIssue = (issue) => {
  if (!issue) return "";
  if (typeof issue === "string") return cleanSentence(issue);
  if (typeof issue === "object") {
    const severity = issue.severity || issue.level || issue.type || "";
    const message = issue.message || issue.description || issue.details || issue.issue || issue.name || issue.title || issue.text || "";
    const line = issue.line || issue.line_number || issue.lineNumber || "";
    let result = cleanSentence(message);
    if (!result) result = "Static analysis issue detected.";
    if (severity) result = `[${String(severity).toUpperCase()}] ${result}`;
    if (line) result += ` (Line ${line})`;
    return result;
  }
  return cleanSentence(String(issue));
};

const normalizeStaticAnalysis = (value) => {
  if (!value) return "No static analysis issues detected.";
  if (Array.isArray(value)) {
    const items = value.map((item) => normalizeIssue(item)).filter(Boolean);
    if (!items.length) return "No static analysis issues detected.";
    return items.map((item, index) => `${index + 1}. ${item}`).join("\n");
  }
  if (typeof value === "object") {
    if (Array.isArray(value.issues)) return normalizeStaticAnalysis(value.issues);
    if (Array.isArray(value.errors)) return normalizeStaticAnalysis(value.errors);
    const normalized = normalizeIssue(value);
    return normalized || "No static analysis issues detected.";
  }
  const text = cleanTextValue(value);
  return text || "No static analysis issues detected.";
};


/* =========================================================
   ROOT CAUSE / FIX HELPERS
========================================================= */

const hasRealStaticIssues = (value) => {
  if (!value) return false;
  const noIssuePatterns = [
    /^no static analysis issues detected\.?$/i,
    /^no issues detected\.?$/i,
    /^no static analysis issues found\.?$/i,
    /^no issues found\.?$/i,
    /^none\.?$/i,
    /^clean\.?$/i,
  ];
  const isRealMessage = (message) => {
    const normalized = cleanSentence(message);
    return Boolean(normalized) && !noIssuePatterns.some((pattern) => pattern.test(normalized));
  };
  if (Array.isArray(value)) return value.some((item) => isRealMessage(normalizeIssue(item)));
  if (typeof value === "object") {
    if (Array.isArray(value.issues)) return hasRealStaticIssues(value.issues);
    if (Array.isArray(value.errors)) return hasRealStaticIssues(value.errors);
    return isRealMessage(normalizeIssue(value));
  }
  return isRealMessage(value);
};

const getIssueMessages = (value) => {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((item) => normalizeIssue(item)).filter(Boolean);
  if (typeof value === "object") {
    if (Array.isArray(value.issues)) return getIssueMessages(value.issues);
    if (Array.isArray(value.errors)) return getIssueMessages(value.errors);
    const item = normalizeIssue(value);
    return item ? [item] : [];
  }
  const text = cleanSentence(value);
  return text ? [text] : [];
};

const buildBugText = (backend, parsed, staticAnalysis) => {
  const directBug = cleanSentence(backend.bug || backend.error || backend.issue || parsed.bug);
  const noBugPatterns = [
    /^no specific bug detected\.?$/i,
    /^no static analysis issues detected\.?$/i,
    /^no issues detected\.?$/i,
    /^no issues found\.?$/i,
    /^none\.?$/i,
    /^clean\.?$/i,
  ];
  if (directBug && !noBugPatterns.some((pattern) => pattern.test(directBug))) return directBug;
  const source = backend.static_analysis || backend.staticAnalysis || backend.issues || staticAnalysis;
  if (hasRealStaticIssues(source)) {
    const messages = getIssueMessages(source);
    if (messages.length > 0) return messages[0];
  }
  return "No specific bug detected.";
};

const buildSuggestedFix = (backend, parsed, staticAnalysis) => {
  const backendSuggestedFixes = backend.suggested_fixes || backend.suggestedFixes || [];
  if (Array.isArray(backendSuggestedFixes)) {
    const cleanedSuggestedFixes = backendSuggestedFixes
      .map((fix) => {
        if (typeof fix === "string") return cleanSentence(fix);
        if (fix && typeof fix === "object") {
          return cleanSentence(fix.message || fix.description || fix.fix || fix.suggested_fix || fix.suggestedFix || "");
        }
        return "";
      })
      .filter(Boolean);
    if (cleanedSuggestedFixes.length > 0) return [...new Set(cleanedSuggestedFixes)].join("\n");
  }
  const directFix = cleanSentence(backend.suggested_fix || backend.suggestedFix || backend.fix || backend.recommended_fix || backend.recommendedFix || parsed.suggestedFix);
  if (directFix) return directFix;
  const automaticFixes = backend.automatic_fixes || backend.automaticFixes || backend.fixes || backend.applied_fixes || backend.appliedFixes || [];
  if (Array.isArray(automaticFixes)) {
    const cleanedFixes = automaticFixes
      .map((fix) => {
        if (typeof fix === "string") return cleanSentence(fix);
        if (fix && typeof fix === "object") {
          return cleanSentence(fix.message || fix.description || fix.fix || fix.suggested_fix || fix.suggestedFix || "");
        }
        return "";
      })
      .filter(Boolean);
    if (cleanedFixes.length > 0) return [...new Set(cleanedFixes)].join(" ");
  }
  const source = backend.static_analysis || backend.staticAnalysis || backend.issues || staticAnalysis;
  const issueMessages = hasRealStaticIssues(source) ? getIssueMessages(source) : [];
  if (issueMessages.length > 0) {
    const specificFixes = [];
    issueMessages.forEach((issueMessage) => {
      const message = cleanSentence(issueMessage);
      const htmlMatch = message.match(/missing closing tag\s+<\/([^>]+)>/i);
      if (htmlMatch) {
        specificFixes.push(`Add the missing closing tag </${htmlMatch[1]}> after the corresponding opening tag content.`);
        return;
      }
      const undefinedVariableMatch = message.match(/undefined variable\s+'([^']+)'/i);
      if (undefinedVariableMatch) {
        const variable = undefinedVariableMatch[1];
        const replacement = { qty: "quantity", usr: "user", amt: "amount", totl: "total" }[variable.toLowerCase()];
        specificFixes.push(replacement ? `Replace undefined variable '${variable}' with '${replacement}'.` : `Define '${variable}' before using it.`);
        return;
      }
      if (/off-by-one/i.test(message)) {
        specificFixes.push("Change '<=' to '<' in the loop condition.");
        return;
      }
      if (/missing semicolon/i.test(message)) { specificFixes.push("Add the missing semicolon at the end of the CSS declaration."); return; }
      if (/missing closing delimiter/i.test(message)) { specificFixes.push("Add the missing closing delimiter to balance the code structure."); return; }
      if (/mismatched delimiter/i.test(message)) { specificFixes.push("Replace the mismatched delimiter with the expected closing delimiter."); return; }
      if (/python syntax error/i.test(message)) { specificFixes.push("Correct the Python syntax described in the detected error and run the analyzer again."); return; }
      if (message) specificFixes.push(`Review and correct the detected issue: ${message}.`);
    });
    const uniqueFixes = [...new Set(specificFixes.filter(Boolean))];
    if (uniqueFixes.length > 0) return uniqueFixes.join(" ");
  }
  return "No fix is required because no static analysis issue was detected.";
};


/* =========================================================
   IMPROVEMENTS
========================================================= */

const normalizeImprovementText = (value) => {
  if (Array.isArray(value)) {
    return value
      .map((item) => (item && typeof item === "object") ? normalizeIssue(item) : cleanSentence(item))
      .filter(Boolean)
      .map((item, index) => `${index + 1}. ${item}`)
      .join("\n");
  }
  if (value && typeof value === "object") {
    if (Array.isArray(value.improvements)) return normalizeImprovementText(value.improvements);
    return Object.values(value)
      .map((item) => (item && typeof item === "object") ? normalizeIssue(item) : cleanSentence(item))
      .filter(Boolean)
      .map((item, index) => `${index + 1}. ${item}`)
      .join("\n");
  }
  const text = cleanTextValue(value);
  if (!text) return "";
  if (text.includes(",") && !text.includes("\n")) {
    const parts = text.split(",").map((item) => item.trim()).filter(Boolean);
    if (parts.length > 1) return parts.map((item, index) => `${index + 1}. ${item}`).join("\n");
  }
  return text;
};


/* =========================================================
   AI RESULT PARSER
========================================================= */

const parseAIResult = (text = "") => {
  const result = {
    staticAnalysis: "No static analysis issues detected.",
    postFixAnalysis: "No post-fix static analysis issues detected.",
    bug: "",
    severity: "NONE",
    explanation: "",
    rootCause: "",
    suggestedFix: "",
    correctedCode: "",
    improvements: "",
    security: { riskLevel: "LOW", issues: [] },
    postFixSecurity: { riskLevel: "LOW", issues: [] },
    complexity: normalizeComplexity(null),
    warnings: [],
  };
  if (!text) return result;
  const cleanText = String(text).replace(/\r/g, "").trim();
  const extractSection = (startPattern, endPatterns) => {
    const startMatch = cleanText.match(startPattern);
    if (!startMatch) return "";
    const startIndex = startMatch.index + startMatch[0].length;
    let endIndex = cleanText.length;
    for (const pattern of endPatterns) {
      const remaining = cleanText.slice(startIndex);
      const match = remaining.match(pattern);
      if (match && typeof match.index === "number") {
        const candidate = startIndex + match.index;
        if (candidate < endIndex) endIndex = candidate;
      }
    }
    return cleanText.slice(startIndex, endIndex).trim();
  };

  const bug = extractSection(/(?:^|\n)BUG DETECTED:\s*/i, [/(?:^|\n)SEVERITY:\s*/i]);
  const severity = extractSection(/(?:^|\n)SEVERITY:\s*/i, [/(?:^|\n)CODE QUALITY SCORE:\s*/i, /(?:^|\n)EXPLANATION:\s*/i, /(?:^|\n)ROOT CAUSE:\s*/i, /(?:^|\n)SUGGESTED FIX:\s*/i]);
  const explanation = extractSection(/(?:^|\n)EXPLANATION:\s*/i, [/(?:^|\n)ROOT CAUSE:\s*/i]);
  const rootCause = extractSection(/(?:^|\n)ROOT CAUSE:\s*/i, [/(?:^|\n)SUGGESTED FIX:\s*/i]);
  const suggestedFix = extractSection(/(?:^|\n)SUGGESTED FIX:\s*/i, [/(?:^|\n)CORRECTED CODE:\s*/i]);
  const correctedCode = extractSection(/(?:^|\n)CORRECTED CODE:\s*/i, [/(?:^|\n)TEST CASE GENERATION:\s*/i, /(?:^|\n)IMPROVEMENTS:\s*/i, /(?:^|\n)STATIC ANALYSIS:\s*/i]);
  const testCaseSection = extractSection(/(?:^|\n)TEST CASE GENERATION:\s*/i, [/(?:^|\n)IMPROVEMENTS:\s*/i, /(?:^|\n)STATIC ANALYSIS:\s*/i]);
  const improvements = extractSection(/(?:^|\n)IMPROVEMENTS:\s*/i, [/(?:^|\n)STATIC ANALYSIS:\s*/i]);
  const staticAnalysis = extractSection(/(?:^|\n)STATIC ANALYSIS:\s*/i, [/(?:^|\n)POST-FIX STATIC ANALYSIS:\s*/i, /(?:^|\n)POST FIX STATIC ANALYSIS:\s*/i]);
  const postFixAnalysis = extractSection(/(?:^|\n)(?:POST-FIX STATIC ANALYSIS|POST FIX STATIC ANALYSIS):\s*/i, [/(?:^|\n)POST-FIX SECURITY VALIDATION:\s*/i, /(?:^|\n)POST FIX SECURITY VALIDATION:\s*/i, /(?:^|\n)WARNINGS:\s*/i]);
  const securitySection = extractSection(/(?:^|\n)SECURITY ANALYSIS:\s*/i, [/(?:^|\n)EXPLANATION:\s*/i, /(?:^|\n)ROOT CAUSE:\s*/i]);
  const postFixSecuritySection = extractSection(/(?:^|\n)(?:POST-FIX SECURITY VALIDATION|POST FIX SECURITY VALIDATION):\s*/i, [/(?:^|\n)WARNINGS:\s*/i]);
  const warningsSection = extractSection(/(?:^|\n)WARNINGS:\s*/i, []);

  result.bug = cleanSentence(bug);
  result.severity = String(severity || "NONE").trim().split(/\s+/)[0].toUpperCase();
  result.explanation = cleanSentence(explanation);
  result.rootCause = cleanSentence(rootCause);
  result.suggestedFix = cleanSentence(suggestedFix);
  result.correctedCode = correctedCode.trim();
  result.improvements = normalizeImprovementText(improvements);
  result.staticAnalysis = normalizeStaticAnalysis(staticAnalysis);
  result.postFixAnalysis = normalizeStaticAnalysis(postFixAnalysis);

  if (securitySection) {
    const riskMatch = securitySection.match(/Security Risk:\s*(CRITICAL|HIGH|MEDIUM|LOW|NONE)/i);
    if (riskMatch) result.security.riskLevel = riskMatch[1].toUpperCase();
  }
  if (postFixSecuritySection) {
    const riskMatch = postFixSecuritySection.match(/Security Risk:\s*(CRITICAL|HIGH|MEDIUM|LOW|NONE)/i);
    if (riskMatch) result.postFixSecurity.riskLevel = riskMatch[1].toUpperCase();
  }
  if (warningsSection) {
    const warningLines = warningsSection.split("\n").map((line) => line.trim()).filter(Boolean).filter((line) => !/^No warnings\.?$/i.test(line));
    result.warnings = warningLines;
  }

  return { ...result, testCaseSection };
};


/* =========================================================
   FILE LANGUAGE DETECTION
========================================================= */

const getLanguageFromFile = (fileName = "") => {
  const extension = fileName.split(".").pop().toLowerCase();
  switch (extension) {
    case "py": return "Python";
    case "js":
    case "jsx": return "JavaScript";
    case "java": return "Java";
    case "c":
    case "h": return "C";
    case "cpp":
    case "hpp": return "C++";
    case "html":
    case "htm": return "HTML";
    case "css": return "CSS";
    default: return "Python";
  }
};


/* =========================================================
   TEST CASE GENERATION (FRONTEND FALLBACK)
========================================================= */

const generateTestCases = (language, sourceCode, correctedCode) => {
  // eslint-disable-next-line no-unused-vars
  const activeCode = correctedCode || sourceCode || "";
  const tests = [];

  switch (language) {
    case "Python":
      tests.push(
        { name: "Normal Execution", input: "Valid sample input", expected: "Program completes successfully" },
        { name: "Boundary Values", input: "Zero / empty / minimum values", expected: "Program handles boundary values" },
        { name: "Invalid Input", input: "Unexpected input", expected: "Program handles invalid input safely" }
      );
      break;
    case "JavaScript":
      tests.push(
        { name: "Normal Execution", input: "Valid JavaScript input", expected: "Expected result is returned" },
        { name: "Empty Input", input: "Empty or null value", expected: "Input is handled safely" },
        { name: "Invalid Input", input: "Invalid value", expected: "No unhandled exception" }
      );
      break;
    case "Java":
      tests.push(
        { name: "Normal Execution", input: "Valid input", expected: "Program returns expected output" },
        { name: "Boundary Input", input: "Minimum or zero value", expected: "Boundary case is handled" },
        { name: "Invalid Input", input: "Invalid value", expected: "Program handles input safely" }
      );
      break;
    case "C":
    case "C++":
      tests.push(
        { name: "Normal Execution", input: "Valid input", expected: "Expected output" },
        { name: "Boundary Values", input: "Zero / minimum input", expected: "Boundary conditions handled" },
        { name: "Invalid Input", input: "Unexpected value", expected: "No crash or undefined behavior" }
      );
      break;
    case "HTML":
      tests.push(
        { name: "Page Rendering", input: "Open HTML page", expected: "Page renders correctly" },
        { name: "Required Elements", input: "Inspect page structure", expected: "Required elements are present" },
        { name: "Broken References", input: "Check links and assets", expected: "No broken references" }
      );
      break;
    case "CSS":
      tests.push(
        { name: "Normal Rendering", input: "Load stylesheet", expected: "Styles apply correctly" },
        { name: "Responsive Layout", input: "Resize viewport", expected: "Layout remains usable" },
        { name: "Invalid Rule", input: "Inspect CSS syntax", expected: "No major stylesheet errors" }
      );
      break;
    default:
      tests.push({ name: "Normal Execution", input: "Valid input", expected: "Expected output" });
  }

  return tests;
};


/* =========================================================
   COMPLEXITY NORMALIZATION
========================================================= */

const normalizeComplexity = (complexity) => {
  if (!complexity || typeof complexity !== "object") {
    return {
      totalLines: 0, codeLines: 0, blankLines: 0, commentLines: 0,
      functions: 0, classes: 0, cyclomaticComplexity: null,
      maxNestingDepth: 0, longLines: 0, averageLineLength: 0,
      complexityLevel: "UNKNOWN", maintainabilityIndex: 0,
    };
  }
  return {
    totalLines: Number(complexity.total_lines ?? complexity.totalLines ?? complexity.lines ?? complexity.line_count ?? complexity.lineCount ?? 0),
    codeLines: Number(complexity.code_lines ?? complexity.codeLines ?? complexity.non_blank_lines ?? complexity.nonBlankLines ?? 0),
    blankLines: Number(complexity.blank_lines ?? complexity.blankLines ?? 0),
    commentLines: Number(complexity.comment_lines ?? complexity.commentLines ?? 0),
    functions: Number(complexity.functions ?? complexity.function_count ?? complexity.functionCount ?? 0),
    classes: Number(complexity.classes ?? complexity.class_count ?? complexity.classCount ?? 0),
    cyclomaticComplexity: complexity.cyclomatic_complexity ?? complexity.cyclomaticComplexity ?? complexity.cyclomatic ?? null,
    maxNestingDepth: Number(complexity.max_nesting_depth ?? complexity.maxNestingDepth ?? complexity.nesting_depth ?? complexity.nestingDepth ?? 0),
    longLines: Number(complexity.long_lines ?? complexity.longLines ?? 0),
    averageLineLength: Number(complexity.average_line_length ?? complexity.averageLineLength ?? complexity.avg_line_length ?? complexity.avgLineLength ?? 0),
    complexityLevel: String(complexity.complexity_level ?? complexity.complexityLevel ?? complexity.level ?? "UNKNOWN").toUpperCase(),
    maintainabilityIndex: Number(complexity.maintainability_index ?? complexity.maintainabilityIndex ?? complexity.maintainability ?? 0),
  };
};


/* =========================================================
   SECURITY NORMALIZATION
========================================================= */

const normalizeBackendSecurity = (security) => {
  if (!security || typeof security !== "object") return { riskLevel: "LOW", issues: [] };
  const issues = Array.isArray(security.issues) ? security.issues : Array.isArray(security.errors) ? security.errors : [];
  return {
    riskLevel: String(security.risk_level || security.riskLevel || "LOW").toUpperCase(),
    issues: issues.map((issue) => {
      if (typeof issue === "string") return { title: issue, severity: "MEDIUM", details: "", fix: "" };
      return {
        title: issue.title || issue.name || issue.type || "Security Issue",
        severity: String(issue.severity || "MEDIUM").toUpperCase(),
        details: issue.details || issue.description || "",
        fix: issue.fix || issue.suggested_fix || "",
      };
    }),
  };
};


/* =========================================================
   FRONTEND SECURITY FALLBACK
========================================================= */

const getSecurityAnalysis = (sourceCode) => {
  const code = String(sourceCode || "");
  const issues = [];
  const addIssue = (title, severity, details, fix) => issues.push({ title, severity, details, fix });

  if (/password\s*=\s*["'][^"']+["']/i.test(code) || /admin_password\s*=\s*["'][^"']+["']/i.test(code)) {
    addIssue("Hardcoded Password", "HIGH", "A password appears to be stored directly in source code.", "Move credentials to environment variables or a secure secrets manager.");
  }
  if (/\b(api[_-]?key|secret[_-]?key)\s*=\s*["'][^"']+["']/i.test(code)) {
    addIssue("Hardcoded API Key or Secret", "HIGH", "A possible API key or secret is directly embedded in the source code.", "Store secrets outside the source code.");
  }
  if (/\beval\s*\(/i.test(code)) addIssue("Use of eval()", "HIGH", "Dynamic evaluation can execute unintended code.", "Avoid eval() and use explicit parsing or validation.");
  if (/\bexec\s*\(/i.test(code)) addIssue("Use of exec()", "HIGH", "Dynamic execution can allow unsafe code execution.", "Avoid dynamic execution and validate inputs.");
  if (/\bos\.system\s*\(/i.test(code)) addIssue("os.system() Usage", "HIGH", "Shell command execution can become dangerous.", "Use safer subprocess APIs.");
  if (/shell\s*=\s*True/i.test(code)) addIssue("subprocess shell=True", "HIGH", "Shell execution can increase command-injection risk.", "Prefer shell=False and pass arguments as a list.");
  if (/(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]{0,150}(?:\+|f["']|%s|\.format\()/i.test(code)) addIssue("Possible SQL Injection", "HIGH", "SQL appears to be constructed dynamically.", "Use parameterized queries or prepared statements.");
  if (/http:\/\//i.test(code) && !/localhost|127\.0\.0\.1/i.test(code)) addIssue("Unencrypted HTTP", "MEDIUM", "The code contains a non-HTTPS URL.", "Use HTTPS for sensitive communication.");
  if (/\bpickle\.load[s]?\s*\(/i.test(code)) addIssue("Unsafe Pickle Deserialization", "HIGH", "Untrusted pickle data can execute arbitrary code.", "Avoid loading untrusted pickle data.");
  if (/verify\s*=\s*False/i.test(code)) addIssue("TLS Verification Disabled", "MEDIUM", "Certificate verification has been disabled.", "Keep TLS certificate verification enabled.");
  if (/chmod\s*\(\s*[^,]+,\s*0?777/i.test(code)) addIssue("Overly Permissive File Permissions", "MEDIUM", "Permissions may allow unrestricted access.", "Use the least permissions required.");

  let riskLevel = "LOW";
  if (issues.some((issue) => issue.severity === "CRITICAL")) riskLevel = "CRITICAL";
  else if (issues.some((issue) => issue.severity === "HIGH")) riskLevel = "HIGH";
  else if (issues.some((issue) => issue.severity === "MEDIUM")) riskLevel = "MEDIUM";
  return { riskLevel, issues };
};


/* =========================================================
   CODE QUALITY
========================================================= */

const getCodeQuality = (sourceCode, staticAnalysis, security) => {
  const code = String(sourceCode || "").trim();
  if (!code) return { overall: 0, readability: 0, structure: 0, errorHandling: 0, maintainability: 0 };

  const lines = code.split("\n").map((line) => line.trimEnd());
  let readability = 100;
  let structure = 92;
  let errorHandling = 100;
  let maintainability = 96;

  const longLines = lines.filter((line) => line.length > 100).length;
  readability -= Math.min(30, longLines * 5);
  const functions = (code.match(/\b(?:def|function|public\s+static|private\s+static|void|int|float|string)\b/g) || []).length;
  if (functions === 0) structure -= 4;
  if (!/try\s*{|try\s*:|catch\s*\(/i.test(code) && code.length > 250) errorHandling -= 6;
  if (/#|\/\/|\/\*/.test(code)) maintainability += 2;
  if (/TODO|FIXME/i.test(code)) maintainability -= 4;
  if (/possible undefined|undefined name|syntax error|static-analysis/i.test(String(staticAnalysis || ""))) structure -= 8;

  if (security?.issues?.length > 0) {
    const securityPenalty = security.issues.reduce((total, issue) => {
      if (issue.severity === "CRITICAL") return total + 12;
      if (issue.severity === "HIGH") return total + 8;
      if (issue.severity === "MEDIUM") return total + 4;
      return total + 1;
    }, 0);
    maintainability -= Math.min(20, securityPenalty);
  }

  readability = Math.max(0, Math.min(100, readability));
  structure = Math.max(0, Math.min(100, structure));
  errorHandling = Math.max(0, Math.min(100, errorHandling));
  maintainability = Math.max(0, Math.min(100, maintainability));
  const overall = Math.round((readability + structure + errorHandling + maintainability) / 4);

  return { overall, readability, structure, errorHandling, maintainability };
};


/* =========================================================
   EXPORT DATA NORMALIZATION

   IMPORTANT:
   Complexity comes directly from `result.complexity` (the same
   object the UI shows). We do NOT recalculate it from the source.
========================================================= */

const buildExportSnapshot = (result, sourceCode, testCases, language, fileName) => {
  const safeResult = result || {};
  const source = String(sourceCode || "");

  const staticAnalysisSource = safeResult.staticAnalysis ?? safeResult.static_analysis ?? safeResult.issues ?? safeResult.errors ?? "";
  const postFixSource = safeResult.postFixAnalysis ?? safeResult.post_fix_analysis ?? "";

  const normalizedStaticAnalysis = normalizeStaticAnalysis(staticAnalysisSource);
  const normalizedPostFixAnalysis = normalizeStaticAnalysis(postFixSource);

  const complexity = normalizeComplexity(
    safeResult.complexity ||
    safeResult.complexity_analysis ||
    safeResult.complexityAnalysis ||
    safeResult.metrics ||
    {}
  );

  const security = normalizeBackendSecurity(safeResult.security);
  const postFixSecurity = normalizeBackendSecurity(safeResult.postFixSecurity || safeResult.post_fix_security || safeResult.postFixSecurityAnalysis || {});

  const finalSecurity = security.issues.length > 0 || security.riskLevel !== "LOW" ? security : getSecurityAnalysis(source);

  const rawCorrectedCode = safeResult.correctedCode || safeResult.corrected_code || "";
  const correctedCode = String(rawCorrectedCode).trim() ? String(rawCorrectedCode) : String(source || "");

  const finalPostFixSecurity = postFixSecurity.issues.length > 0 || postFixSecurity.riskLevel !== "LOW"
    ? postFixSecurity
    : getSecurityAnalysis(correctedCode);

  const quality = safeResult.quality || getCodeQuality(source, normalizedStaticAnalysis, finalSecurity);

  return {
    language: safeResult.language || safeResult.programming_language || language || "Python",
    fixStatus: safeResult.fixStatus || safeResult.fix_status || "none",
    fileName: fileName || "Manual Code Input",
    bug: cleanSentence(safeResult.bug || safeResult.error || safeResult.issue) || "No specific bug detected.",
    severity: String(safeResult.severity || "NONE").toUpperCase().trim(),
    quality,
    complexity,
    security: finalSecurity,
    explanation: cleanSentence(safeResult.explanation) || "No explanation was provided.",
    rootCause: cleanSentence(safeResult.rootCause || safeResult.root_cause) || "No root cause was provided.",
    suggestedFix: cleanSentence(safeResult.suggestedFix || safeResult.suggested_fix || safeResult.fix) || "No suggested fix was provided.",
    correctedCode,
    testCases: Array.isArray(testCases) ? testCases : [],
    improvements: String(safeResult.improvements || "No improvement notes were provided."),
    staticAnalysis: normalizedStaticAnalysis,
    postFixAnalysis: normalizedPostFixAnalysis,
    postFixSecurity: finalPostFixSecurity,
    warnings: Array.isArray(safeResult.warnings)
      ? safeResult.warnings.map((warning) => normalizeIssue(warning)).filter(Boolean)
      : [],
  };
};


/* =========================================================
   COMPONENT
========================================================= */

function Analyzer() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Python");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [fileName, setFileName] = useState("");
  const [testCases, setTestCases] = useState([]);

  const handleGithubCodeLoaded = ({ code: githubCode, language: githubLanguage, fileName: githubFileName }) => {
    setCode(githubCode || "");
    setLanguage(githubLanguage || "Python");
    setFileName(githubFileName || "");
    setResult(null);
    setError("");
    setTestCases([]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const supportedExtensions = [".py", ".js", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp", ".html", ".htm", ".css"];
    const lowerName = file.name.toLowerCase();
    const isSupported = supportedExtensions.some((extension) => lowerName.endsWith(extension));

    if (!isSupported) {
      setError("Unsupported file type. Please upload Python, JavaScript, Java, C, C++, HTML or CSS files.");
      return;
    }
    if (file.size > 15 * 1024) {
      setError("File is too large. Please upload a file below 15 KB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const uploadedCode = String(reader.result || "");
      if (uploadedCode.length > 15000) {
        setError("Code is too large. Please keep the code below 15,000 characters.");
        return;
      }
      setCode(uploadedCode);
      setLanguage(getLanguageFromFile(file.name));
      setFileName(file.name);
      setResult(null);
      setError("");
      setTestCases([]);
    };
    reader.onerror = () => setError("Could not read the selected file.");
    reader.readAsText(file);
    event.target.value = "";
  };

  const handleAnalyze = async () => {
    setError("");
    setCopied(false);
    setCopiedCode(false);

    if (!code.trim()) {
      setError("Please enter or upload code before analyzing.");
      return;
    }
    if (code.length > 15000) {
      setError("Code is too large. Please keep the code below 15,000 characters.");
      return;
    }

    setLoading(true);

    try {
      const data = await analyzeCode(code, language);
      if (!data?.success) throw new Error(data?.message || "Analysis failed.");

      const backend = data || {};
      const parsed = parseAIResult(data.ai_analysis?.response || data.ai_analysis?.message || "");

      const backendSecurity = normalizeBackendSecurity(backend.security);
      const frontendSecurity = getSecurityAnalysis(code);
      const security = backendSecurity.issues.length > 0 ? backendSecurity : frontendSecurity;

      const correctedCode = String(backend.corrected_code || backend.correctedCode || parsed.correctedCode || "").trim() || code;

      const backendPostFixSecurity = normalizeBackendSecurity(
        backend.post_fix_security || backend.postFixSecurity || backend.post_fix_security_analysis || backend.postFixSecurityAnalysis
      );
      const postFixFrontendSecurity = getSecurityAnalysis(correctedCode);
      const postFixSecurity = backendPostFixSecurity.issues.length > 0 ? backendPostFixSecurity : postFixFrontendSecurity;

      const reportLanguage = backend.language || backend.programming_language || language || getLanguageFromFile(fileName) || "Python";

      const rawStaticAnalysis = backend.static_analysis ?? backend.staticAnalysis ?? backend.issues ?? parsed.staticAnalysis;
      const normalizedStaticAnalysis = normalizeStaticAnalysis(rawStaticAnalysis);

      const rawPostFixAnalysis =
        backend.post_fix_static_analysis ??
        backend.post_fix_analysis ??
        backend.postFixAnalysis ??
        parsed.postFixAnalysis;
      const normalizedPostFixAnalysis = normalizeStaticAnalysis(rawPostFixAnalysis);

      const bug = buildBugText(backend, parsed, rawStaticAnalysis);

      let rootCause = cleanSentence(backend.root_cause || backend.rootCause || parsed.rootCause);
      if (!rootCause) {
        if (hasRealStaticIssues(rawStaticAnalysis)) {
          const messages = getIssueMessages(rawStaticAnalysis);
          if (messages.length > 0) rootCause = `The detected problem is caused by: ${messages[0]}.`;
        }
      }
      if (!rootCause) rootCause = "No root cause was identified because no static analysis issue was detected.";

      const suggestedFix = buildSuggestedFix(backend, parsed, rawStaticAnalysis);

      let severity = String(backend.severity || parsed.severity || "NONE").toUpperCase().trim();
      const hasStaticIssues = hasRealStaticIssues(rawStaticAnalysis);
      if (severity === "NONE" && hasStaticIssues) severity = "HIGH";

      let explanation = cleanSentence(backend.explanation || parsed.explanation);
      if (!explanation) {
        explanation = bug !== "No specific bug detected."
          ? `The ${reportLanguage} static analyzer detected a code issue. The problem is related to ${bug.toLowerCase()}.`
          : "The analyzer did not find a specific issue in the submitted code.";
      }

      const improvements = normalizeImprovementText(backend.improvements || parsed.improvements);

      let warnings = [];
      if (Array.isArray(backend.warnings)) {
        warnings = backend.warnings.map((warning) => normalizeIssue(warning)).filter(Boolean);
      } else {
        warnings = parsed.warnings.map((warning) => normalizeIssue(warning)).filter(Boolean);
      }

      const backendQuality = backend.quality_score || {};
      const quality = backendQuality.overall !== undefined
        ? {
            overall: backendQuality.overall,
            readability: backendQuality.readability || 0,
            structure: backendQuality.code_structure || 0,
            errorHandling: backendQuality.error_handling || 0,
            maintainability: backendQuality.maintainability || 0,
          }
        : getCodeQuality(code, normalizedStaticAnalysis, security);

      const normalizedResult = {
        language: reportLanguage,
        bug,
        severity,
        explanation,
        rootCause,
        suggestedFix,
        correctedCode: correctedCode.trim(),
        fixStatus: backend.fix_status || "none",
        improvements: improvements || "No improvement notes were provided.",
        staticAnalysis: normalizedStaticAnalysis,
        postFixAnalysis: normalizedPostFixAnalysis,
        security,
        postFixSecurity,
        complexity: normalizeComplexity(backend.complexity || backend.complexity_analysis || backend.metrics),
        quality,
        warnings,
      };

      const generatedTests = backend.test_cases && backend.test_cases.length > 0
        ? backend.test_cases.map((tc) => ({
            name: tc.name || "Test Case",
            input: tc.input || "",
            expected: tc.expected_output || tc.expected || ""
          }))
        : generateTestCases(reportLanguage, code, correctedCode);

      setResult(normalizedResult);
      setTestCases(generatedTests);

      if (data.analysis_id) console.log("Analysis ID:", data.analysis_id);

    } catch (err) {
      console.error("Analyzer error:", err);
      setError(err?.response?.data?.message || err?.message || "Analysis failed. Please check the backend and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setCode("");
    setResult(null);
    setError("");
    setCopied(false);
    setCopiedCode(false);
    setFileName("");
    setTestCases([]);
  };

  const getSeverityClass = (severity) => {
    switch (String(severity || "NONE").toUpperCase()) {
      case "CRITICAL": return "severity-critical";
      case "HIGH": return "severity-high";
      case "MEDIUM": return "severity-medium";
      case "LOW": return "severity-low";
      default: return "severity-none";
    }
  };

  const getIssueClass = (severity) => {
    switch (String(severity || "MEDIUM").toUpperCase()) {
      case "CRITICAL": return "severity-critical";
      case "HIGH": return "severity-high";
      case "MEDIUM": return "severity-medium";
      case "LOW": return "severity-low";
      default: return "severity-medium";
    }
  };

  /* =======================================================
     CORRECTED CODE HEADING HELPERS
  ======================================================= */

  const getCorrectedCodeHeading = () => {
    if (result.fixStatus === "partial") return "Partially Fixed Code (Manual Review Needed)";
    if (result.fixStatus === "skipped") return "Your Original Code (Manual Fix Needed)";
    if (result.fixStatus === "none" && result.security?.riskLevel === "HIGH") {
      return "Code Unchanged (Security Issues Need Manual Review)";
    }
    return "Corrected Code";
  };

  const getCorrectedCodeToolbarLabel = () => {
    if (result.fixStatus === "partial") return "Partially Fixed Code";
    if (result.fixStatus === "skipped") return "Unchanged Code";
    return "Fixed Code";
  };

  const shouldShowSafeMessage = () => {
    return (
      (result.fixStatus === "none" || result.fixStatus === "skipped") &&
      result.security?.riskLevel === "HIGH" &&
      !result.correctedCode
    );
  };

  /* =======================================================
     REPORT TEXT
  ======================================================= */

  const buildReportText = () => {
    if (!result) return "";

    const report = buildExportSnapshot(result, code, testCases, language, fileName);

    const securityText = report.security.issues.length === 0
      ? "No common security-risk patterns were detected by the local security scanner."
      : report.security.issues.map((issue, index) =>
          `${index + 1}. ${issue.title} [${issue.severity}]\nDetails: ${issue.details}\nFix: ${issue.fix}`
        ).join("\n\n");

    const postFixSecurityText = report.postFixSecurity.issues.length === 0
      ? "No common security-risk patterns were detected after automatic fixes."
      : report.postFixSecurity.issues.map((issue, index) =>
          `${index + 1}. ${issue.title} [${issue.severity}]\nDetails: ${issue.details}\nFix: ${issue.fix}`
        ).join("\n\n");

    const testsText = report.testCases.length === 0
      ? "No test cases were generated."
      : report.testCases.map((test, index) =>
          `${index + 1}. ${test.name}\nInput: ${test.input}\nExpected Output: ${test.expected}`
        ).join("\n\n");

    const warningsText = report.warnings.length === 0
      ? "No warnings."
      : report.warnings.map((warning, index) => `${index + 1}. ${warning}`).join("\n");

    const correctedCodeHeading =
      report.fixStatus === "partial"
        ? "PARTIALLY FIXED CODE (MANUAL REVIEW NEEDED):"
        : report.fixStatus === "skipped"
          ? "YOUR ORIGINAL CODE (MANUAL FIX NEEDED):"
          : (report.fixStatus === "none" && report.security?.riskLevel === "HIGH")
            ? "CODE UNCHANGED (SECURITY ISSUES NEED MANUAL REVIEW):"
            : "CORRECTED CODE:";

    const correctedCodeNote =
      report.fixStatus === "partial"
        ? "Some issues (off-by-one, syntax) were auto-fixed, but the missing nested brace could not be safely auto-fixed. Please review the corrected code and apply the remaining fix manually.\n\n"
        : report.fixStatus === "skipped"
          ? "Automatic fixing was not possible because the missing brace is in a nested block. Please apply the fix manually.\n\n"
          : (report.fixStatus === "none" && report.security?.riskLevel === "HIGH")
            ? "The auto-fix engine does not modify security-sensitive patterns (like eval() or hardcoded credentials). Please apply the recommendations in the SECURITY ANALYSIS section manually.\n\n"
            : "";

    return `AI SOFTWARE BUG ANALYZER
========================

AI ANALYSIS REPORT

PROGRAMMING LANGUAGE:
${report.language}

UPLOADED FILE:
${report.fileName}

BUG DETECTED:
${report.bug}

SEVERITY:
${report.severity}

CODE QUALITY SCORE:
Overall: ${report.quality.overall}/100
Readability: ${report.quality.readability}/100
Code Structure: ${report.quality.structure}/100
Error Handling: ${report.quality.errorHandling}/100
Maintainability: ${report.quality.maintainability}/100

COMPLEXITY ANALYSIS:
Total Lines: ${report.complexity.totalLines}
Code Lines: ${report.complexity.codeLines}
Blank Lines: ${report.complexity.blankLines}
Comment Lines: ${report.complexity.commentLines}
Functions: ${report.complexity.functions}
Classes: ${report.complexity.classes}
Cyclomatic Complexity: ${report.complexity.cyclomaticComplexity ?? "N/A"}
Maximum Nesting Depth: ${report.complexity.maxNestingDepth}
Long Lines: ${report.complexity.longLines}
Average Line Length: ${report.complexity.averageLineLength}
Complexity Level: ${report.complexity.complexityLevel}
Maintainability Index: ${report.complexity.maintainabilityIndex}/100

SECURITY ANALYSIS:
Security Risk: ${report.security.riskLevel}

${securityText}

EXPLANATION:
${report.explanation}

ROOT CAUSE:
${report.rootCause}

SUGGESTED FIX:
${report.suggestedFix}

${correctedCodeHeading}
${correctedCodeNote}${report.correctedCode || "No corrected code was generated."}

TEST CASE GENERATION:
${testsText}

IMPROVEMENTS:
${report.improvements}

STATIC ANALYSIS:
${report.staticAnalysis}

POST-FIX STATIC ANALYSIS:
${report.postFixAnalysis}

POST-FIX SECURITY VALIDATION:
Security Risk: ${report.postFixSecurity.riskLevel}

${postFixSecurityText}

WARNINGS:
${warningsText}

========================
Analysis completed successfully
========================`;
  };

  const handleCopyReport = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(buildReportText());
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (err) {
      console.error("Copy report error:", err);
    }
  };

  const handleCopyCorrectedCode = async () => {
    if (!result?.correctedCode) return;
    try {
      await navigator.clipboard.writeText(result.correctedCode);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 1800);
    } catch (err) {
      console.error("Copy corrected code error:", err);
    }
  };

  const downloadTXTReport = () => {
    if (!result) return;
    const report = buildReportText();
    const blob = new Blob([report], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "BugAI_Analysis_Report.txt";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  /* =======================================================
     PDF REPORT
  ======================================================= */

  const downloadPDFReport = () => {
    if (!result) return;

    const report = buildExportSnapshot(result, code, testCases, language, fileName);
    const doc = new jsPDF({ orientation: "p", unit: "mm", format: "a4" });

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 15;
    const contentWidth = pageWidth - margin * 2;
    const bottomLimit = pageHeight - 24;

    let y = 18;

    doc.setProperties({
      title: "AI Software Bug Analyzer - Analysis Report",
      subject: "AI Software Bug Analyzer Report",
      author: "BugAI",
    });

    const drawHeader = () => {
      const currentPage = doc.getCurrentPageInfo().pageNumber;
      if (currentPage === 1) {
        doc.setFillColor(245, 247, 255);
        doc.roundedRect(margin, y, contentWidth, 21, 3, 3, "F");
        doc.setTextColor(38, 43, 82);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(15);
        doc.text("AI SOFTWARE BUG ANALYZER", margin + 7, y + 8);
        doc.setFontSize(9);
        doc.setTextColor(92, 99, 122);
        doc.setFont("helvetica", "normal");
        doc.text("AI ANALYSIS REPORT", margin + 7, y + 15);
        y += 28;
      } else {
        y = 18;
      }
    };

    const ensureSpace = (requiredHeight = 10) => {
      if (y + requiredHeight > bottomLimit) {
        doc.addPage();
        y = 18;
        drawHeader();
      }
    };

    const drawSectionTitle = (title, iconText = "") => {
      ensureSpace(16);
      doc.setFillColor(238, 242, 255);
      doc.roundedRect(margin, y, contentWidth, 9, 2, 2, "F");
      doc.setTextColor(67, 56, 202);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(10);
      doc.text(`${iconText}${title}`, margin + 5, y + 6.2);
      y += 14;
    };

    const drawParagraph = (text, options = {}) => {
      const value = String(text === undefined || text === null ? "" : text);
      if (!value.trim()) {
        doc.setTextColor(100, 100, 100);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.text("No information available.", margin, y);
        y += 7;
        return;
      }
      const fontSize = options.fontSize || 9.5;
      const lineHeight = options.lineHeight || 4.7;
      const lines = doc.splitTextToSize(value, contentWidth - 8);
      ensureSpace(lines.length * lineHeight + 5);
      doc.setTextColor(45, 45, 55);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(fontSize);
      lines.forEach((line) => {
        ensureSpace(lineHeight + 2);
        doc.text(line, margin + 4, y);
        y += lineHeight;
      });
      y += 2;
    };

    const drawCodeBlock = (value) => {
      const rawText = String(value == null ? "" : value);
      const codeText = rawText.trim() ? rawText : "No corrected code was generated.";
      const codeLines = codeText.split("\n");
      const lineHeight = 4.2;
      const padding = 4;
      const charWidth = 1.55;
      const currentHeight = Math.max(14, codeLines.length * lineHeight + padding * 2);
      const maxBlockHeight = pageHeight - 42;

      if (currentHeight > maxBlockHeight) {
        const linesPerPage = Math.floor((maxBlockHeight - padding * 2) / lineHeight);
        let index = 0;
        while (index < codeLines.length) {
          ensureSpace(Math.min(maxBlockHeight, linesPerPage * lineHeight + padding * 2) + 4);
          const chunk = codeLines.slice(index, index + linesPerPage);
          const blockHeight = chunk.length * lineHeight + padding * 2;
          doc.setFillColor(248, 250, 252);
          doc.setDrawColor(226, 232, 240);
          doc.roundedRect(margin, y, contentWidth, blockHeight, 2, 2, "FD");
          doc.setTextColor(31, 41, 55);
          doc.setFont("courier", "normal");
          doc.setFontSize(7.8);
          chunk.forEach((line, lineIndex) => {
            const safeLine = line.length > 115 ? `${line.slice(0, 112)}...` : line;
            const leadingSpaces = safeLine.match(/^ */)[0].length;
            const indentedLine = safeLine.slice(leadingSpaces);
            doc.text(indentedLine, margin + padding + leadingSpaces * charWidth, y + padding + 3.2 + lineIndex * lineHeight);
          });
          y += blockHeight + 5;
          index += linesPerPage;
          if (index < codeLines.length) {
            doc.addPage();
            y = 18;
            drawHeader();
          }
        }
        return;
      }

      ensureSpace(currentHeight + 5);
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(margin, y, contentWidth, currentHeight, 2, 2, "FD");
      doc.setTextColor(31, 41, 55);
      doc.setFont("courier", "normal");
      doc.setFontSize(7.8);
      codeLines.forEach((line, index) => {
        const safeLine = line.length > 115 ? `${line.slice(0, 112)}...` : line;
        const leadingSpaces = safeLine.match(/^ */)[0].length;
        const indentedLine = safeLine.slice(leadingSpaces);
        doc.text(indentedLine, margin + padding + leadingSpaces * charWidth, y + padding + 3.2 + index * lineHeight);
      });
      y += currentHeight + 5;
      doc.setFont("helvetica", "normal");
    };

    const drawLabelValue = (label, value) => {
      ensureSpace(13);
      doc.setFillColor(249, 250, 251);
      doc.roundedRect(margin, y, contentWidth, 12, 2, 2, "F");
      doc.setTextColor(75, 85, 99);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8.5);
      doc.text(label, margin + 4, y + 7);
      doc.setTextColor(31, 41, 55);
      doc.setFont("helvetica", "normal");
      const valueLines = doc.splitTextToSize(String(value || ""), contentWidth - 4 - 42);
      doc.text(valueLines[0] || "", margin + 42, y + 7);
      y += 15;
      if (valueLines.length > 1) {
        valueLines.slice(1).forEach((line) => {
          ensureSpace(5);
          doc.text(line, margin + 42, y);
          y += 4.5;
        });
      }
    };

    const drawSecurityIssues = (security) => {
      if (!security || !security.issues || security.issues.length === 0) {
        doc.setFillColor(236, 253, 245);
        const safeText = "No common security-risk patterns were detected by the local security scanner.";
        const lines = doc.splitTextToSize(safeText, contentWidth - 10);
        const boxHeight = lines.length * 4.7 + 8;
        ensureSpace(boxHeight + 3);
        doc.roundedRect(margin, y, contentWidth, boxHeight, 2, 2, "F");
        doc.setTextColor(5, 118, 90);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8.7);
        lines.forEach((line, index) => {
          doc.text(line, margin + 5, y + 6 + index * 4.7);
        });
        y += boxHeight + 4;
        return;
      }

      security.issues.forEach((issue, index) => {
        const title = `${index + 1}. ${issue.title}`;
        const details = issue.details || "No additional details provided.";
        const fix = issue.fix || "Review the code and apply secure coding practices.";
        const detailLines = doc.splitTextToSize(details, contentWidth - 10);
        const fixLines = doc.splitTextToSize(`Fix: ${fix}`, contentWidth - 10);
        const boxHeight = 23 + detailLines.length * 4.2 + fixLines.length * 4.2;
        ensureSpace(Math.min(boxHeight, pageHeight - 40) + 3);

        doc.setFillColor(255, 247, 237);
        doc.setDrawColor(253, 186, 116);
        doc.roundedRect(margin, y, contentWidth, boxHeight, 2, 2, "FD");
        doc.setTextColor(124, 45, 18);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.text(title, margin + 5, y + 7);
        doc.setFontSize(7.8);
        doc.text(`Severity: ${issue.severity}`, margin + 5, y + 12);
        doc.setTextColor(55, 65, 81);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8.2);

        let issueY = y + 17;
        detailLines.forEach((line) => {
          doc.text(line, margin + 5, issueY);
          issueY += 4.2;
        });
        issueY += 1;
        fixLines.forEach((line) => {
          doc.text(line, margin + 5, issueY);
          issueY += 4.2;
        });
        y += boxHeight + 4;
      });
    };

    const drawQualityCard = (quality) => {
      ensureSpace(40);
      const boxHeight = 39;
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(margin, y, contentWidth, boxHeight, 3, 3, "FD");
      doc.setTextColor(17, 24, 39);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(18);
      doc.text(`${quality.overall}/100`, margin + 8, y + 13);
      doc.setFontSize(8);
      doc.setTextColor(100, 116, 139);
      doc.text("Overall Quality", margin + 8, y + 19);

      const metrics = [
        ["Readability", quality.readability],
        ["Code Structure", quality.structure],
        ["Error Handling", quality.errorHandling],
        ["Maintainability", quality.maintainability],
      ];
      const startX = margin + 67;
      const columnWidth = (contentWidth - 74) / 2;

      metrics.forEach((item, index) => {
        const col = index % 2;
        const row = Math.floor(index / 2);
        const x = startX + col * columnWidth;
        const metricY = y + 9 + row * 13;
        doc.setTextColor(71, 85, 105);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.text(item[0], x, metricY);
        doc.setTextColor(30, 41, 59);
        doc.setFont("helvetica", "bold");
        doc.text(`${item[1]}/100`, x + columnWidth - 20, metricY);
      });
      y += boxHeight + 5;
    };

    const drawComplexityCard = (complexity) => {
      const items = [
        ["Total Lines", complexity.totalLines],
        ["Code Lines", complexity.codeLines],
        ["Blank Lines", complexity.blankLines],
        ["Comment Lines", complexity.commentLines],
        ["Functions", complexity.functions],
        ["Classes", complexity.classes],
        ["Cyclomatic Complexity", complexity.cyclomaticComplexity ?? "N/A"],
        ["Max Nesting Depth", complexity.maxNestingDepth],
        ["Long Lines", complexity.longLines],
        ["Average Line Length", complexity.averageLineLength],
        ["Complexity Level", complexity.complexityLevel],
        ["Maintainability Index", `${complexity.maintainabilityIndex}/100`],
      ];
      const rows = Math.ceil(items.length / 2);
      const boxHeight = 12 + rows * 10;
      ensureSpace(boxHeight + 2);
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(margin, y, contentWidth, boxHeight, 3, 3, "FD");

      items.forEach((item, index) => {
        const col = index % 2;
        const row = Math.floor(index / 2);
        const x = margin + 7 + col * (contentWidth / 2);
        const itemY = y + 8 + row * 10;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(7.5);
        doc.setTextColor(71, 85, 105);
        doc.text(item[0], x, itemY);
        doc.setFont("helvetica", "bold");
        doc.setTextColor(30, 41, 59);
        doc.text(String(item[1]), x + (contentWidth / 2) - 20, itemY);
      });
      y += boxHeight + 5;
    };

    const drawTestCases = (tests) => {
      if (!tests.length) {
        drawParagraph("No test cases were generated.");
        return;
      }
      tests.forEach((test, index) => {
        const inputText = `Input: ${test.input}`;
        const expectedText = `Expected Output: ${test.expected}`;
        const inputLines = doc.splitTextToSize(inputText, contentWidth - 12);
        const expectedLines = doc.splitTextToSize(expectedText, contentWidth - 12);
        const cardHeight = 19 + (inputLines.length + expectedLines.length) * 4.3;
        ensureSpace(cardHeight + 3);
        doc.setFillColor(249, 250, 251);
        doc.setDrawColor(226, 232, 240);
        doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, "FD");
        doc.setTextColor(31, 41, 55);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(8.7);
        doc.text(`${index + 1}. ${test.name}`, margin + 5, y + 7);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8.1);
        let testY = y + 12;
        inputLines.forEach((line) => { doc.text(line, margin + 5, testY); testY += 4.3; });
        expectedLines.forEach((line) => { doc.text(line, margin + 5, testY); testY += 4.3; });
        y += cardHeight + 4;
      });
    };

    /* =====================================================
       BUILD PDF
    ===================================================== */

    drawHeader();

    drawSectionTitle("REPORT INFORMATION");
    drawLabelValue("Programming Language:", report.language);
    drawLabelValue("Uploaded File:", report.fileName);

    drawSectionTitle("BUG DETECTED");
    drawParagraph(report.bug);

    drawSectionTitle("SEVERITY");
    ensureSpace(17);
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(margin, y, contentWidth, 15, 2, 2, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(30, 41, 59);
    doc.text(report.severity, margin + 6, y + 9.5);
    y += 20;

    drawSectionTitle("CODE QUALITY SCORE");
    drawQualityCard(report.quality);

    drawSectionTitle("COMPLEXITY ANALYSIS");
    drawComplexityCard(report.complexity);

    drawSectionTitle("SECURITY ANALYSIS");
    ensureSpace(15);
    doc.setTextColor(45, 55, 72);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text(`Security Risk: ${report.security.riskLevel}`, margin + 1, y);
    y += 6;
    drawSecurityIssues(report.security);
    drawParagraph(
      "Security analysis checks common code patterns. It is a first-level scanner and does not replace a professional security audit.",
      { fontSize: 7.8, lineHeight: 4.1 }
    );

    drawSectionTitle("EXPLANATION");
    drawParagraph(report.explanation);

    drawSectionTitle("ROOT CAUSE");
    drawParagraph(report.rootCause);

    drawSectionTitle("SUGGESTED FIX");
    drawParagraph(report.suggestedFix);

    drawSectionTitle(
      report.fixStatus === "partial"
        ? "PARTIALLY FIXED CODE (MANUAL REVIEW NEEDED)"
        : report.fixStatus === "skipped"
          ? "YOUR ORIGINAL CODE (MANUAL FIX NEEDED)"
          : (report.fixStatus === "none" && report.security?.riskLevel === "HIGH")
            ? "CODE UNCHANGED (SECURITY ISSUES NEED MANUAL REVIEW)"
            : "CORRECTED CODE"
    );

    if (report.fixStatus === "partial") {
      drawParagraph(
        "Some issues (off-by-one, syntax) were auto-fixed, but the missing nested brace could not be safely auto-fixed. Please review the corrected code and apply the remaining fix manually."
      );
    } else if (report.fixStatus === "skipped") {
      drawParagraph(
        "Automatic fixing was not possible because the missing brace is in a nested block. Please apply the fix manually."
      );
    } else if (report.fixStatus === "none" && report.security?.riskLevel === "HIGH") {
      drawParagraph(
        "The auto-fix engine does not modify security-sensitive patterns (like eval() or hardcoded credentials). Please apply the recommendations in the SECURITY ANALYSIS section manually."
      );
    }

    drawCodeBlock(report.correctedCode);

    drawSectionTitle("TEST CASE GENERATION");
    drawTestCases(report.testCases);

    drawSectionTitle("IMPROVEMENTS");
    drawParagraph(report.improvements);

    drawSectionTitle("STATIC ANALYSIS");
    drawParagraph(report.staticAnalysis);

    drawSectionTitle("POST-FIX STATIC ANALYSIS");
    drawParagraph(report.postFixAnalysis);

    drawSectionTitle("POST-FIX SECURITY VALIDATION");
    ensureSpace(15);
    doc.setTextColor(45, 55, 72);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text(`Security Risk: ${report.postFixSecurity.riskLevel}`, margin + 1, y);
    y += 6;
    if (report.postFixSecurity.issues.length === 0) {
      drawParagraph("No common security-risk patterns were detected after automatic fixes.");
    } else {
      drawSecurityIssues(report.postFixSecurity);
    }
    drawParagraph(
      "The corrected code was checked again after automatic fixes were applied.",
      { fontSize: 7.8, lineHeight: 4.1 }
    );

    drawSectionTitle("WARNINGS");
    if (report.warnings.length === 0) {
      drawParagraph("No warnings.");
    } else {
      report.warnings.forEach((warning, index) => {
        drawParagraph(`${index + 1}. ${warning}`);
      });
    }

    ensureSpace(20);
    doc.setFillColor(236, 253, 245);
    doc.roundedRect(margin, y, contentWidth, 16, 3, 3, "F");
    doc.setTextColor(5, 118, 90);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.text("Analysis completed successfully", pageWidth / 2, y + 10, { align: "center" });

    const totalPages = doc.getNumberOfPages();
    for (let page = 1; page <= totalPages; page++) {
      doc.setPage(page);
      doc.setDrawColor(226, 232, 240);
      doc.line(margin, pageHeight - 14, pageWidth - margin, pageHeight - 14);
      doc.setTextColor(100, 116, 139);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.5);
      doc.text("BugAI | AI Software Bug Analyzer & Code Fixer", margin, pageHeight - 8);
      doc.text(`Page ${page} of ${totalPages}`, pageWidth - margin, pageHeight - 8, { align: "right" });
    }

    doc.save("BugAI_Analysis_Report.pdf");
  };


  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <main className="analyzer-page">

      <div className="analyzer-header">
        <div className="analyzer-header-inner">
          <div>
            <span className="analyzer-eyebrow">AI POWERED DEVELOPMENT TOOL</span>
            <h1>AI Software Bug Analyzer</h1>
            <p>Detect bugs, understand root causes, fix code and validate the result automatically.</p>
          </div>
          <div className="analyzer-header-icon"><FaRobot /></div>
        </div>
      </div>

      <div className="analyzer-container">

        <GitHubImport onCodeLoaded={handleGithubCodeLoaded} />

        <section className="analyzer-card">
          <div className="analyzer-card-header">
            <div>
              <span className="section-label">CODE ANALYZER</span>
              <h2>Submit Your Code</h2>
              <p>Enter code, upload a source file, or import code from GitHub.</p>
            </div>
          </div>

          <div className="analyzer-toolbar">
            <div className="analyzer-language-group">
              <label htmlFor="language">Programming Language</label>
              <select
                id="language"
                value={language}
                onChange={(event) => { setLanguage(event.target.value); setResult(null); }}
                className="analyzer-select"
              >
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="Java">Java</option>
                <option value="C">C</option>
                <option value="C++">C++</option>
                <option value="HTML">HTML</option>
                <option value="CSS">CSS</option>
              </select>
            </div>

            <label className="upload-button">
              <FaUpload />
              Upload File
              <input
                type="file"
                accept=".py,.js,.jsx,.java,.c,.cpp,.h,.hpp,.html,.htm,.css"
                onChange={handleFileUpload}
                hidden
              />
            </label>

            <button type="button" className="clear-button" onClick={handleClear}>Clear</button>
          </div>

          {fileName && (
            <div className="uploaded-file-info"><FaCode /><span>{fileName}</span></div>
          )}

          <div className="analyzer-editor-wrapper">
            <textarea
              className="analyzer-editor"
              value={code}
              onChange={(event) => { setCode(event.target.value); setResult(null); }}
              placeholder={"Paste your code here...\n\nExample:\n\ndef calculate_total(price, quantity):\n    return price * quantity"}
              spellCheck={false}
            />
          </div>

          <div className="editor-footer">
            <span>{code.length} / 15,000 characters</span>
            <span>{language}</span>
          </div>

          {error && (
            <div className="analyzer-error">
              <FaExclamationTriangle />
              <span>{error}</span>
            </div>
          )}

          <div className="analyze-actions">
            <button
              type="button"
              className="analyze-button"
              onClick={handleAnalyze}
              disabled={loading || !code.trim()}
            >
              {loading ? (<><span className="button-spinner"></span>Analyzing...</>) : (<><FaSearch />Analyze Code</>)}
            </button>
          </div>
        </section>

        {result && (
          <section className="analysis-result">

            <div className="result-header">
              <div className="result-title">
                <div className="result-icon"><FaRobot /></div>
                <div>
                  <h2>AI Analysis Report</h2>
                  <p><FaCheckCircle /> Analysis completed successfully.</p>
                </div>
              </div>

              <div className="download-buttons">
                <button type="button" className="copy-button" onClick={handleCopyReport}>
                  {copied ? (<><FaCheckCircle />Copied</>) : (<><FaCopy />Copy Report</>)}
                </button>
                <button type="button" className="copy-button" onClick={downloadTXTReport}>
                  <FaDownload /> TXT
                </button>
                <button type="button" className="copy-button" onClick={downloadPDFReport}>
                  <FaDownload /> PDF
                </button>
              </div>
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaCode /><h3>Programming Language</h3></div>
              <p>{result.language}</p>
            </div>

            <div className="report-section bug-section">
              <div className="report-section-title"><FaBug /><h3>Bug Detected</h3></div>
              <p>{result.bug || "No specific bug detected."}</p>
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaExclamationTriangle /><h3>Severity</h3></div>
              <span className={`severity ${getSeverityClass(result.severity)}`}>{result.severity}</span>
            </div>

            <div className="report-section quality-card">
              <div className="report-section-title"><FaBullseye /><h3>Code Quality Score</h3></div>
              <div className="quality-content">
                <div className="quality-score">
                  <strong>{result.quality.overall}</strong>
                  <span>/100</span>
                  <small>Overall</small>
                </div>
                <div className="quality-metrics">
                  <div><span>Readability</span><strong>{result.quality.readability}/100</strong></div>
                  <div><span>Code Structure</span><strong>{result.quality.structure}/100</strong></div>
                  <div><span>Error Handling</span><strong>{result.quality.errorHandling}/100</strong></div>
                  <div><span>Maintainability</span><strong>{result.quality.maintainability}/100</strong></div>
                </div>
              </div>
            </div>

            <div className="report-section complexity-section">
              <div className="report-section-title">
                <FaBullseye />
                <h3>Complexity Analysis</h3>
                <span className="complexity-level">{result.complexity.complexityLevel}</span>
              </div>
              <div className="complexity-grid">
                <div><span>Total Lines</span><strong>{result.complexity.totalLines}</strong></div>
                <div><span>Code Lines</span><strong>{result.complexity.codeLines}</strong></div>
                <div><span>Blank Lines</span><strong>{result.complexity.blankLines}</strong></div>
                <div><span>Comment Lines</span><strong>{result.complexity.commentLines}</strong></div>
                <div><span>Functions</span><strong>{result.complexity.functions}</strong></div>
                <div><span>Classes</span><strong>{result.complexity.classes}</strong></div>
                <div><span>Cyclomatic Complexity</span><strong>{result.complexity.cyclomaticComplexity ?? "N/A"}</strong></div>
                <div><span>Max Nesting Depth</span><strong>{result.complexity.maxNestingDepth}</strong></div>
                <div><span>Long Lines</span><strong>{result.complexity.longLines}</strong></div>
                <div><span>Average Line Length</span><strong>{result.complexity.averageLineLength}</strong></div>
                <div><span>Maintainability</span><strong>{result.complexity.maintainabilityIndex}/100</strong></div>
              </div>
            </div>

            <div className="report-section security-section">
              <div className="report-section-title">
                <FaExclamationTriangle />
                <h3>Security Analysis</h3>
                <span className={`security-badge ${getSeverityClass(result.security.riskLevel)}`}>{result.security.riskLevel}</span>
              </div>
              {result.security.issues.length === 0 ? (
                <div className="security-safe">
                  <FaCheckCircle />
                  <p>No common security-risk patterns were detected by the local security scanner.</p>
                </div>
              ) : (
                <div className="security-issues">
                  {result.security.issues.map((issue, index) => (
                    <div className="security-issue-card" key={`${issue.title}-${index}`}>
                      <div className="security-issue-header">
                        <strong>{index + 1}. {issue.title}</strong>
                        <span className={`severity ${getIssueClass(issue.severity)}`}>{issue.severity}</span>
                      </div>
                      {issue.details && <p>{issue.details}</p>}
                      {issue.fix && <div className="security-fix"><FaWrench /><span>{issue.fix}</span></div>}
                    </div>
                  ))}
                </div>
              )}
              <div className="security-note">
                Security analysis checks common code patterns. It is a first-level scanner and does not replace a professional security audit.
              </div>
            </div>

            <div className="report-section explanation-section">
              <div className="report-section-title"><FaLightbulb /><h3>Explanation</h3></div>
              <p>{result.explanation || "No explanation was provided."}</p>
            </div>

            <div className="report-section root-cause-section">
              <div className="report-section-title"><FaBullseye /><h3>Root Cause</h3></div>
              <p>{result.rootCause || "No root cause was provided."}</p>
            </div>

            <div className="report-section fix-section">
              <div className="report-section-title"><FaWrench /><h3>Suggested Fix</h3></div>
              <p>{result.suggestedFix || "Review the detected issue and apply the recommended correction."}</p>
            </div>

            <div className="report-section corrected-code">
              <div className="report-section-title">
                <FaCode />
                <h3>{getCorrectedCodeHeading()}</h3>
              </div>

              {shouldShowSafeMessage() ? (
                <div className="safe-message">
                  <p>
                    The auto-fix engine does not modify security-sensitive
                    patterns (like <code>eval()</code> or hardcoded credentials).
                    Please apply the recommendations in the{" "}
                    <strong>Security Analysis</strong> section manually.
                  </p>
                </div>
              ) : (
                <>
                  <div className="corrected-code-toolbar">
                    <span>{getCorrectedCodeToolbarLabel()}</span>
                    <button type="button" className="copy-button" onClick={handleCopyCorrectedCode}>
                      {copiedCode ? (<><FaCheckCircle />Copied</>) : (<><FaCopy />Copy Code</>)}
                    </button>
                  </div>
                  <pre>
                    <code>{result.correctedCode || "No corrected code was generated."}</code>
                  </pre>
                </>
              )}
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaSearch /><h3>Test Case Generation</h3></div>
              {testCases.length === 0 ? (
                <div className="safe-message">No test cases were generated.</div>
              ) : (
                <div className="test-cases">
                  {testCases.map((test, index) => (
                    <div className="test-case" key={`${test.name}-${index}`}>
                      <div className="test-case-header">
                        <span>{index + 1}</span>
                        <strong>{test.name}</strong>
                      </div>
                      <div className="test-case-row">
                        <strong>Input</strong>
                        <code>{test.input}</code>
                      </div>
                      <div className="test-case-row">
                        <strong>Expected Output</strong>
                        <code>{test.expected}</code>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaLightbulb /><h3>Improvements</h3></div>
              <div className="improvements-content">
                {String(result.improvements || "No improvement notes were provided.")
                  .split("\n")
                  .map((item, index) => (<p key={`improvement-${index}`}>{item}</p>))}
              </div>
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaSearch /><h3>Static Analysis</h3></div>
              <pre className="analysis-text">{normalizeStaticAnalysis(result.staticAnalysis)}</pre>
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaCheckCircle /><h3>Post-Fix Static Analysis</h3></div>
              <pre className="analysis-text">{normalizeStaticAnalysis(result.postFixAnalysis)}</pre>
            </div>

            <div className="report-section security-section">
              <div className="report-section-title">
                <FaCheckCircle />
                <h3>Post-Fix Security Validation</h3>
                <span className={`security-badge ${getSeverityClass(result.postFixSecurity.riskLevel)}`}>{result.postFixSecurity.riskLevel}</span>
              </div>
              {result.postFixSecurity.issues.length === 0 ? (
                <div className="security-safe">
                  <FaCheckCircle />
                  <p>No common security-risk patterns were detected after automatic fixes.</p>
                </div>
              ) : (
                <div className="security-issues">
                  {result.postFixSecurity.issues.map((issue, index) => (
                    <div className="security-issue-card" key={`post-${issue.title}-${index}`}>
                      <div className="security-issue-header">
                        <strong>{index + 1}. {issue.title}</strong>
                        <span className={`severity ${getIssueClass(issue.severity)}`}>{issue.severity}</span>
                      </div>
                      {issue.details && <p>{issue.details}</p>}
                      {issue.fix && <div className="security-fix"><FaWrench /><span>{issue.fix}</span></div>}
                    </div>
                  ))}
                </div>
              )}
              <div className="security-note">The corrected code was checked again after automatic fixes were applied.</div>
            </div>

            <div className="report-section">
              <div className="report-section-title"><FaExclamationTriangle /><h3>Warnings</h3></div>
              {result.warnings.length === 0 ? (
                <div className="safe-message"><FaCheckCircle />No warnings.</div>
              ) : (
                <div className="warnings-list">
                  {result.warnings.map((warning, index) => (
                    <div className="warning-item" key={`warning-${index}`}>
                      <span>{index + 1}</span>
                      <p>{warning}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="analysis-success-footer">
              <FaCheckCircle />
              <span>Analysis completed successfully</span>
            </div>

          </section>
        )}

      </div>

    </main>
  );
}


export default Analyzer;