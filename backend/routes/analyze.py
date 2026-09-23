from flask import Blueprint, request, jsonify
from services.ai_service import analyze_code
from models.analysis_model import save_analysis

analyze_bp = Blueprint("analyze", __name__)

def safe_text(value, default=""):
    if value is None: return default
    if isinstance(value, str): return value
    if isinstance(value, list): return "\n".join(str(item) for item in value) if value else default
    if isinstance(value, dict): return "\n".join(f"{key}: {item}" for key, item in value.items())
    return str(value)

def format_issue_list(issues):
    if not issues: return "No issues detected."
    lines = []
    for index, issue in enumerate(issues, start=1):
        if isinstance(issue, dict):
            severity = issue.get("severity", issue.get("level", "INFO"))
            message = issue.get("message", issue.get("description", issue.get("issue", str(issue))))
            lines.append(f"{index}. [{severity}] {message}")
        else:
            lines.append(f"{index}. {issue}")
    return "\n".join(lines)

def format_test_cases(test_cases):
    if not test_cases: return "No test cases generated."
    lines = []
    for index, test_case in enumerate(test_cases, start=1):
        if isinstance(test_case, dict):
            name = test_case.get("name", test_case.get("title", f"Test Case {index}"))
            description = test_case.get("description", "")
            input_value = test_case.get("input", "")
            expected = test_case.get("expected_output", test_case.get("expected", ""))
            lines.append(f"Test Case {index}: {name}")
            if description: lines.append(f"Description: {description}")
            if input_value != "": lines.append(f"Input: {input_value}")
            if expected != "": lines.append(f"Expected: {expected}")
            lines.append("")
        else:
            lines.append(f"Test Case {index}: {test_case}")
    return "\n".join(lines).strip()

def format_complexity(complexity):
    if not complexity: return "No complexity analysis available."
    if not isinstance(complexity, dict): return str(complexity)
    labels = [("total_lines", "Total Lines"), ("code_lines", "Code Lines"), ("blank_lines", "Blank Lines"), ("comment_lines", "Comment Lines"), ("functions", "Functions"), ("classes", "Classes"), ("cyclomatic_complexity", "Cyclomatic Complexity"), ("maximum_nesting_depth", "Maximum Nesting Depth"), ("long_lines", "Long Lines"), ("average_line_length", "Average Line Length"), ("complexity_level", "Complexity Level"), ("maintainability_index", "Maintainability Index")]
    lines = [f"{label}: {complexity[key]}" for key, label in labels if key in complexity]
    if not lines:
        for key, value in complexity.items(): lines.append(f"{key}: {value}")
    return "\n".join(lines)

def build_security_report(security_issues, security_risk, security_recommendations=None):
    lines = [f"Security Risk: {security_risk or 'LOW'}", ""]
    if security_issues:
        lines.append("Security Issues:")
        for index, issue in enumerate(security_issues, start=1):
            if isinstance(issue, dict):
                severity = issue.get("severity", issue.get("level", "INFO"))
                message = issue.get("message", issue.get("description", issue.get("issue", str(issue))))
                lines.append(f"{index}. [{severity}] {message}")
            else:
                lines.append(f"{index}. {issue}")
    else:
        lines.append("No common security-risk patterns were detected by the local security scanner.")
    lines.append("")
    lines.append("Security Recommendations:")
    if security_recommendations:
        if isinstance(security_recommendations, list):
            for index, recommendation in enumerate(security_recommendations, start=1): lines.append(f"{index}. {recommendation}")
        else:
            lines.append(str(security_recommendations))
    else:
        lines.append("No security recommendations available.")
    return "\n".join(lines)

def build_history_report(result):
    if not isinstance(result, dict): return str(result)
    language = result.get("programming_language", result.get("language", "Unknown"))
    issues = result.get("issues", result.get("static_analysis", []))
    security_issues = result.get("security_issues", [])
    severity = result.get("severity", "NONE")
    explanation = result.get("explanation", "No explanation available.")
    root_cause = result.get("root_cause", "No root cause information available.")
    suggested_fixes = result.get("suggested_fixes", result.get("suggested_fix", []))
    automatic_fixes = result.get("automatic_fixes", [])
    corrected_code = result.get("corrected_code", "")
    improvements = result.get("improvements", [])
    warnings = result.get("warnings", [])
    test_cases = result.get("test_cases", [])
    security_risk = result.get("security_risk", "LOW")
    security_recommendations = result.get("security_recommendations", [])
    complexity = result.get("complexity", result.get("complexity_analysis", result.get("metrics", {})))
    post_fix_security = result.get("post_fix_security_analysis", {})
    post_fix_static = result.get("post_fix_static_analysis", [])
    post_fix_security_risk = result.get("post_fix_security_risk", None)
    if not post_fix_security_risk:
        if isinstance(post_fix_security, dict):
            post_fix_security_risk = post_fix_security.get("risk_level", "LOW")
        else:
            post_fix_security_risk = "LOW" if not post_fix_security else "HIGH"
    quality_score = result.get("quality_score", None)

    lines = [f"Programming Language: {language}", "", "BUG DETECTED"]
    lines.append(format_issue_list(issues) if issues else "No bugs detected.")
    lines.extend(["", "SEVERITY", str(severity), "", "EXPLANATION", safe_text(explanation, "No explanation available."), "", "ROOT CAUSE", safe_text(root_cause, "No root cause information available."), "", "SUGGESTED FIX"])
    if suggested_fixes:
        if isinstance(suggested_fixes, list):
            for index, fix in enumerate(suggested_fixes, start=1): lines.append(f"{index}. {fix}")
        else:
            lines.append(str(suggested_fixes))
    else:
        lines.append("No suggested fix available.")
    lines.extend(["", "AUTOMATIC FIXES"])
    if automatic_fixes:
        if isinstance(automatic_fixes, list):
            for index, fix in enumerate(automatic_fixes, start=1): lines.append(f"{index}. {fix}")
        else:
            lines.append(str(automatic_fixes))
    else:
        lines.append("No automatic fixes were applied.")
    lines.extend(["", "CORRECTED CODE", str(corrected_code) if corrected_code else "No corrected code generated.", "", "IMPROVEMENTS"])
    if improvements:
        if isinstance(improvements, list):
            for index, improvement in enumerate(improvements, start=1): lines.append(f"{index}. {improvement}")
        else:
            lines.append(str(improvements))
    else:
        lines.append("No improvement notes available.")
    lines.extend(["", "WARNINGS"])
    if warnings:
        if isinstance(warnings, list):
            for index, warning in enumerate(warnings, start=1): lines.append(f"{index}. {warning}")
        else:
            lines.append(str(warnings))
    else:
        lines.append("No warnings.")
    lines.extend(["", "SECURITY ANALYSIS", build_security_report(security_issues, security_risk, security_recommendations), "", "COMPLEXITY ANALYSIS", format_complexity(complexity)])
    if quality_score is not None:
        lines.append("")
        lines.append(f"Quality Score: {quality_score.get('overall', 'N/A')}/100" if isinstance(quality_score, dict) else f"Quality Score: {quality_score}/100")
    lines.extend(["", "TEST CASES", format_test_cases(test_cases), "", "STATIC ANALYSIS"])
    lines.append(format_issue_list(issues) if issues else "No static analysis issues detected.")
    lines.extend(["", "POST-FIX SECURITY VALIDATION"])
    if isinstance(post_fix_security, dict):
        post_fix_issues = post_fix_security.get("issues", post_fix_security.get("security_issues", []))
        post_fix_security_risk = post_fix_security.get("risk_level", post_fix_security_risk)
    else:
        post_fix_issues = post_fix_security
    lines.append(f"Security Risk: {post_fix_security_risk}")
    if post_fix_issues:
        lines.append("")
        lines.append(format_issue_list(post_fix_issues) if isinstance(post_fix_issues, list) else str(post_fix_issues))
    else:
        lines.extend(["", "No post-fix security issues detected."])
    lines.extend(["", "POST-FIX STATIC ANALYSIS"])
    if isinstance(post_fix_static, str) and post_fix_static.strip():
        lines.append(post_fix_static)
    elif isinstance(post_fix_static, list) and post_fix_static:
        lines.append(format_issue_list(post_fix_static))
    else:
        lines.append("No post-fix static analysis issues detected.")
    lines.extend(["", "Analysis completed successfully"])
    return "\n".join(lines)

@analyze_bp.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(silent=True)
        if not data: return jsonify({"success": False, "message": "Request body is required."}), 400
        code = data.get("code", "")
        language = data.get("language", "Python")
        user_id = data.get("user_id")
        if not code or not str(code).strip(): return jsonify({"success": False, "message": "Please provide code to analyze."}), 400
        if not user_id: return jsonify({"success": False, "message": "User ID is required."}), 400
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Invalid user ID."}), 400

        print("==========================================")
        print("Starting code analysis...")
        print(f"User ID: {user_id}")
        print(f"Language: {language}")
        print(f"Code length: {len(code)}")

        result = analyze_code(code, language)

        print("===== POST-FIX DEBUG =====")
        print("post_fix_static_analysis value:", repr(result.get("post_fix_static_analysis")))
        print("auto_fix_skipped (via warnings):", result.get("warnings"))
        print("==========================")

        if not isinstance(result, dict):
            return jsonify({"success": False, "message": "Analysis service returned invalid data."}), 500

        history_report = build_history_report(result)
        print("History report generated.")
        print(f"History report length: {len(history_report)}")

        try:
            save_result = save_analysis(user_id=user_id, code=code, language=language, result=history_report)
            print("Analysis saved to database.")
            print(f"Save result: {save_result}")
        except TypeError:
            try:
                save_result = save_analysis(user_id, code, language, history_report)
                print("Analysis saved using positional arguments.")
                print(f"Save result: {save_result}")
            except Exception as save_error:
                print("Database save error:", save_error)
                return jsonify({"success": False, "message": "Analysis completed, but the result could not be saved.", "analysis": result}), 500
        except Exception as save_error:
            print("Database save error:", save_error)
            return jsonify({"success": False, "message": "Analysis completed, but the result could not be saved.", "analysis": result}), 500

        response = dict(result)
        response["success"] = True
        response["language"] = result.get("language", language)
        response["programming_language"] = result.get("programming_language", language)
        response["code"] = code
        response["analysis_completed"] = True
        response["history_saved"] = True

        return jsonify(response), 200

    except Exception as e:
        print("==========================================")
        print("Analysis route error:", e)
        print("==========================================")
        return jsonify({"success": False, "message": "An error occurred while analyzing the code.", "error": str(e)}), 500