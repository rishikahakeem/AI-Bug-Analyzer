import ast
import os
import re
import requests
from .static_analyzer import run_static_analysis

# ============================================================
# CONFIGURATION
# ============================================================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MAX_AI_CODE_LENGTH = 15000
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "20"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "700"))
ENABLE_OLLAMA = os.getenv("ENABLE_OLLAMA", "false").strip().lower() in {"1", "true", "yes", "on"}

def make_issue(message, severity="MEDIUM", line=None, title=None, details=None, fix=None):
    issue = {"message": str(message), "severity": severity}
    if line is not None: issue["line"] = line
    if title is not None: issue["title"] = str(title)
    if details is not None: issue["details"] = str(details)
    if fix is not None: issue["fix"] = str(fix)
    return issue

def normalize_language(language):
    language = str(language or "Python").strip().lower()
    mapping = {"py": "Python", "python": "Python", "js": "JavaScript", "javascript": "JavaScript", "java": "Java", "c": "C", "cpp": "C++", "c++": "C++", "html": "HTML", "htm": "HTML", "css": "CSS"}
    return mapping.get(language, "Python")

def clean_code(code):
    return str(code or "").replace("\r\n", "\n").replace("\r", "\n")

# ============================================================
# SECURITY ANALYSIS
# ============================================================
def security_scan(code, language):
    code = clean_code(code)
    language = normalize_language(language)

    if language == "Python":
        eval_hint = "Avoid eval(). Use ast.literal_eval() for parsing literals, or explicit parsing/validation for expressions."
        exec_hint = "Avoid exec(). Use explicit function dispatch or a safe interpreter for dynamic behavior."
    elif language == "JavaScript":
        eval_hint = "Avoid eval(). Use JSON.parse() for data, or the Function constructor with validated input for dynamic code."
        exec_hint = "Avoid dynamic code execution. Use explicit function dispatch instead."
    elif language == "Java":
        eval_hint = "Avoid dynamic evaluation. Use explicit parsing and validation."
        exec_hint = "Avoid dynamic code execution. Use explicit dispatch instead."
    else:
        eval_hint = "Avoid eval(). Use explicit parsing or validation for expressions."
        exec_hint = "Avoid dynamic code execution. Use explicit function dispatch instead."

    issues = []
    patterns = [
        (r"""(?:password|passwd|pwd)(?:\s*\[\s*\d*\s*\])?\s*[:=]+\s*["'][^"']+["']""",
         "Hardcoded password detected.", "HIGH", "Hardcoded Password",
         "A password appears to be stored directly in the source code.",
         "Move credentials to environment variables or a secure secrets manager."),
        (r"""(?:api[_-]?key|apikey)(?:\s*\[\s*\d*\s*\])?\s*[:=]+\s*["'][^"']+["']""",
         "Possible hardcoded API key detected.", "HIGH", "Hardcoded API Key",
         "A possible API key is embedded directly in the source code.",
         "Store API keys outside the source code."),
        (r"""(?:secret|token)(?:\s*\[\s*\d*\s*\])?\s*[:=]+\s*["'][^"']+["']""",
         "Possible hardcoded secret detected.", "HIGH", "Hardcoded Secret",
         "A secret value is embedded directly in the source code.",
         "Store secrets in environment variables or a secrets manager."),
        (r"""os\.system\s*\(""",
         "os.system() can execute operating-system commands.", "HIGH", "Unsafe os.system() Usage",
         "os.system() runs shell commands directly and is vulnerable to command injection.",
         "Use subprocess.run() with a list of arguments and shell=False."),
        (r"""subprocess\.[a-zA-Z_]+\s*\(""",
         "Subprocess execution detected.", "MEDIUM", "Subprocess Execution",
         "The code spawns external processes, which can be dangerous with untrusted input.",
         "Validate all inputs before passing them to subprocess calls."),
        (r"""shell\s*=\s*True""",
         "shell=True may introduce command-injection risks.", "HIGH", "subprocess shell=True",
         "Running commands with shell=True can allow command injection.",
         "Prefer shell=False and pass arguments as a list."),
        (r"""\beval\s*\(""",
         "eval() can execute arbitrary code.", "HIGH", "Use of eval()",
         f"The eval() function executes arbitrary {language} code from a string. If the string contains user input, this can lead to remote code execution.",
         eval_hint),
        (r"""\bexec\s*\(""",
         "exec() can execute arbitrary code.", "HIGH", "Use of exec()",
         f"The exec() function runs arbitrary {language} code from a string, which is dangerous with untrusted input.",
         exec_hint),
        (r"""SELECT\s+.*\+""",
         "Possible SQL query concatenation detected.", "HIGH", "Possible SQL Injection",
         "A SQL query appears to be built by concatenating strings, which allows SQL injection.",
         "Use parameterized queries (placeholders) instead of string concatenation."),
    ]
    for pattern, message, severity, title, details, fix in patterns:
        try:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(make_issue(message, severity, title=title, details=details, fix=fix))
        except re.error:
            continue

    risk_level = "HIGH" if any(item.get("severity") == "HIGH" for item in issues) else ("MEDIUM" if issues else "LOW")
    return {"risk_level": risk_level, "issues": issues, "message": "Security risks were detected." if issues else "No common security-risk patterns were detected by the local security scanner."}

# ============================================================
# AUTOMATIC FIXES
# ============================================================
def fix_python_syntax(code):
    code = clean_code(code)
    try:
        ast.parse(code)
        return code, []
    except SyntaxError:
        pass
    lines = code.splitlines()
    block_keywords = ("def ", "class ", "if ", "elif ", "else", "for ", "while ", "try ", "except", "finally", "with ", "match ", "case ")
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.endswith(":"): continue
        if not stripped.startswith(block_keywords): continue
        if stripped.startswith("else") and stripped != "else": continue
        if stripped.startswith("try") and stripped != "try": continue
        if stripped.startswith("finally") and stripped != "finally": continue
        candidate_lines = list(lines)
        candidate_lines[index] = (line.rstrip() + ":")
        candidate = "\n".join(candidate_lines)
        try:
            ast.parse(candidate)
            return candidate, [f"Added missing ':' on line {index + 1}."]
        except SyntaxError:
            continue
    return code, []

def fix_common_variables(code):
    corrected = clean_code(code)
    fixes = []
    replacements = {"quanity": "quantity", "lenght": "length", "widht": "width", "heigth": "height", "adress": "address", "recieve": "receive", "seperate": "separate"}
    for wrong, correct in replacements.items():
        pattern = rf"\b{re.escape(wrong)}\b"
        if re.search(pattern, corrected):
            corrected = re.sub(pattern, correct, corrected)
            fixes.append(f"Changed '{wrong}' to '{correct}'.")
    return corrected, fixes

def fix_off_by_one_javascript(code):
    fixes = []
    if not isinstance(code, str) or not code.strip():
        return code, fixes

    prop_pattern = re.compile(
        r"(for\s*\(\s*(?:var|let|int|long|size_t|auto)?\s*\w+\s*=\s*0\s*;\s*)"
        r"(\w+)(\s*<=\s*)"
        r"([\w\.\[\]]+?)((?:\.length|\.size\s*\(\s*\)|\.size)\b)",
        re.IGNORECASE
    )
    def prop_replacer(match):
        line_num = code[:match.start()].count("\n") + 1
        fixes.append(f"Changed '<=' to '<' in loop condition (line {line_num}).")
        prefix, var, _op, target, suffix = match.groups()
        return f"{prefix}{var} < {target}{suffix}"
    corrected = prop_pattern.sub(prop_replacer, code)

    size_var_names = (
        "size", "length", "count", "len", "max", "limit",
        "capacity", "cap", "array_size", "arr_size",
        "items_count", "item_count", "element_count", "elem_count",
        "n", "total_size"
    )
    size_var_pattern = re.compile(
        r"(for\s*\(\s*(?:var|let|int|long|size_t|auto)?\s*\w+\s*=\s*0\s*;\s*)"
        r"(\w+)(\s*<=\s*)"
        r"(\w+)(\s*;)",
        re.IGNORECASE
    )
    def size_var_replacer(match):
        var = match.group(4)
        if var.lower() not in size_var_names:
            return match.group(0)
        line_num = code[:match.start()].count("\n") + 1
        fixes.append(f"Changed '<=' to '<' in loop condition (line {line_num}).")
        return f"{match.group(1)}{match.group(2)} < {match.group(4)}{match.group(5)}"
    corrected = size_var_pattern.sub(size_var_replacer, corrected)

    return corrected, fixes

def fix_off_by_one_python(code):
    fixes = []
    if not isinstance(code, str) or not code.strip():
        return code, fixes
    pattern = re.compile(
        r"(for\s+\w+\s+in\s+range\s*\(\s*len\s*\(\s*[\w\.\[\]]+\s*\))"
        r"(\s*\+\s*1)"
        r"(\s*\))",
        re.IGNORECASE
    )
    def replacer(match):
        line_num = code[:match.start()].count("\n") + 1
        fixes.append(f"Removed '+ 1' from range(len(...)) in loop (line {line_num}).")
        return f"{match.group(1)}{match.group(3)}"
    corrected = pattern.sub(replacer, code)
    return corrected, fixes

def fix_brace_before_else(code):
    fixes = []
    if not isinstance(code, str) or not code.strip():
        return code, fixes

    lines = code.split("\n")
    output = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        is_else = (
            stripped == "else"
            or stripped.startswith("else ")
            or stripped.startswith("else{")
            or stripped.startswith("else if")
            or stripped.startswith("}else")
            or stripped.startswith("} else")
        )

        has_brace_before = stripped.startswith("}")
        if is_else and not has_brace_before and len(output) > 0:
            prev_idx = len(output) - 1
            while prev_idx >= 0 and not output[prev_idx].strip():
                prev_idx -= 1

            if prev_idx >= 0:
                prev_line = output[prev_idx]
                prev_stripped = prev_line.rstrip()
                cur_indent = len(line) - len(line.lstrip())
                prev_indent = len(prev_line) - len(prev_line.lstrip())

                if (
                    prev_indent > cur_indent
                    and prev_stripped
                    and not prev_stripped.endswith("}")
                    and not prev_stripped.endswith("{")
                ):
                    output[prev_idx] = prev_stripped + "}"
                    fixes.append(
                        f"Added missing '}}' before 'else' on line {i + 1}."
                    )

        output.append(line)

    return "\n".join(output), fixes

def _insert_before_trailing_punct(line, insertion):
    stripped = line.rstrip()
    trailing_punct = ""
    while stripped and stripped[-1] in ";,:":
        trailing_punct = stripped[-1] + trailing_punct
        stripped = stripped[:-1]
    trailing_whitespace = line[len(line.rstrip()):]
    return stripped + insertion + trailing_punct + trailing_whitespace

def _indent_of(line):
    return len(line) - len(line.lstrip())

def _is_top_level_starter(stripped):
    if not stripped:
        return False

    if re.match(r"^(class|interface|enum|struct|namespace|union)\s+\w", stripped):
        return True

    if re.match(r"^(?:public|private|protected|static|final|abstract|synchronized|extern|inline|constexpr|const|unsigned|signed|long|short|volatile|register|auto)?\s*"
                r"[A-Za-z_][\w\s\*<>,&:\[\]]*\s+[A-Za-z_]\w*\s*\(", stripped):
        return True
    if re.match(r"^[A-Za-z_]\w*\s*\(", stripped):
        return True

    if stripped.endswith("{"):
        first_part = stripped.split("{")[0].strip()
        if not first_part:
            return False
        if first_part.startswith(("@media", "@supports", "@keyframes", "@font-face", "@import", "@charset")):
            return True
        if re.match(r"^(if|for|while|switch|catch|function|return|else)\b", first_part):
            return False
        if re.match(r"^[A-Za-z\.\#\*\[\:\-\s>\+~\(\)0-9_,%]+$", first_part):
            return True

    return False

def _is_block_keyword_starter(stripped):
    if not stripped:
        return False
    block_keywords = ("else", "else if", "catch", "finally")
    for keyword in block_keywords:
        if stripped == keyword or stripped.startswith(keyword + " ") or stripped.startswith(keyword + "{"):
            return True
    return False

def _find_best_brace_insert_line(lines):
    for i in range(1, len(lines)):
        current = lines[i]
        stripped = current.strip()
        if not stripped:
            continue
        if stripped.startswith(("//", "/*", "*", "#")):
            continue
        if stripped == "}":
            continue

        prev_idx = i - 1
        while prev_idx >= 0 and not lines[prev_idx].strip():
            prev_idx -= 1
        if prev_idx < 0:
            continue
        previous = lines[prev_idx]

        current_indent = _indent_of(current)
        previous_indent = _indent_of(previous)

        if previous_indent <= current_indent:
            continue

        if previous.rstrip().endswith("}"):
            continue

        if (stripped.startswith("return")
                or stripped.startswith("break")
                or stripped.startswith("continue")):
            return i, max(0, current_indent)

        if _is_block_keyword_starter(stripped):
            return i, max(0, current_indent)

        if _is_top_level_starter(stripped):
            return i, max(0, current_indent)

    return None, None

def _count_braces(code):
    return code.count("{"), code.count("}")

def _try_bracket_fix(code, open_char, close_char):
    open_count = code.count(open_char)
    close_count = code.count(close_char)
    if open_count <= close_count:
        return code, None
    missing = open_count - close_count
    lines = code.split("\n")
    for idx in range(len(lines) - 1, -1, -1):
        line = lines[idx]
        if line.count(open_char) > line.count(close_char):
            lines[idx] = _insert_before_trailing_punct(line, close_char * missing)
            return "\n".join(lines), f"Added missing closing '{close_char}' at line {idx + 1}."
    return code, None

def fix_javascript_brackets_smart(code):
    corrected = clean_code(code)
    fixes = []

    corrected, paren_fix = _try_bracket_fix(corrected, "(", ")")
    if paren_fix:
        fixes.append(paren_fix)

    corrected, sq_fix = _try_bracket_fix(corrected, "[", "]")
    if sq_fix:
        fixes.append(sq_fix)

    iteration = 0
    max_iterations = 20
    while iteration < max_iterations:
        open_br, close_br = _count_braces(corrected)
        if open_br == close_br:
            break
        iteration += 1

        if open_br > close_br:
            lines = corrected.split("\n")
            insert_idx, indent_count = _find_best_brace_insert_line(lines)
            if insert_idx is not None:
                brace_line = (" " * indent_count) + "}"
                lines.insert(insert_idx, brace_line)
                fixes.append(f"Added missing closing curly brace at line {insert_idx + 1}.")
                corrected = "\n".join(lines)
            else:
                corrected = corrected.rstrip() + "\n}"
                fixes.append("Added missing closing curly brace at the end of the file.")
        else:
            pos = corrected.rfind("}")
            if pos >= 0:
                corrected = corrected[:pos] + corrected[pos + 1:]
                fixes.append("Removed extra closing curly brace.")
            else:
                break

    return corrected, fixes

def fix_html(code):
    corrected = clean_code(code)
    fixes = []
    if "<html" not in corrected.lower():
        corrected = f"<html>\n<head>\n    <title>Document</title>\n</head>\n<body>\n{corrected}\n</body>\n</html>"
        fixes.append("Added a basic HTML document structure.")
    else:
        for tag in ("head", "body", "html"):
            if corrected.lower().count(f"<{tag}") > corrected.lower().count(f"</{tag}"):
                corrected = corrected.rstrip() + f"\n</{tag}>"
                fixes.append(f"Added missing </{tag}> closing tag.")
    return corrected, fixes

def fix_java_ccpp(code):
    corrected, fixes = fix_javascript_brackets_smart(code)
    lines = corrected.split("\n")
    semicolon_fixes = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith((";", "{", "}", ":", ",")):
            continue
        if stripped.startswith(("#", "//", "/*", "*")):
            continue
        if stripped.endswith(")"):
            if re.match(r"^(return|break|continue|[A-Za-z_]\w*(\s*[\w\[\]\.]*)*\s*=)", stripped):
                lines[idx] = stripped + ";"
                semicolon_fixes.append(f"Added missing semicolon on line {idx + 1}.")
    if semicolon_fixes:
        corrected = "\n".join(lines)
        fixes.extend(semicolon_fixes)
    return corrected, fixes

def apply_automatic_fixes(code, language):
    corrected = clean_code(code)
    fixes = []
    language = normalize_language(language)

    if language == "Python":
        corrected, syntax_fixes = fix_python_syntax(corrected)
        fixes.extend(syntax_fixes)
        corrected, oob_fixes = fix_off_by_one_python(corrected)
        fixes.extend(oob_fixes)
        corrected, variable_fixes = fix_common_variables(corrected)
        fixes.extend(variable_fixes)
    elif language in {"JavaScript", "Java", "C", "C++", "CSS"}:
        if language == "JavaScript":
            corrected, else_fixes = fix_brace_before_else(corrected)
            fixes.extend(else_fixes)
        corrected, bracket_fixes = fix_javascript_brackets_smart(corrected)
        fixes.extend(bracket_fixes)
        if language in {"Java", "C", "C++"}:
            corrected, semicolon_fixes = fix_java_ccpp(corrected)
            fixes.extend(semicolon_fixes)
        if language == "JavaScript":
            corrected, oob_fixes = fix_off_by_one_javascript(corrected)
            fixes.extend(oob_fixes)
        corrected, variable_fixes = fix_common_variables(corrected)
        fixes.extend(variable_fixes)
    elif language == "HTML":
        corrected, html_fixes = fix_html(corrected)
        fixes.extend(html_fixes)

    return corrected, fixes

# ============================================================
# METRICS
# ============================================================
def calculate_severity(static_issues, security_result):
    severities = []
    for item in static_issues:
        if isinstance(item, dict):
            severities.append(str(item.get("severity", "")).upper())
        elif isinstance(item, str):
            lower = item.lower()
            if any(k in lower for k in ("syntax error", "expected ':'", "unmatched", "off-by-one")):
                severities.append("HIGH")
            elif "possible" in lower or "warning" in lower:
                severities.append("MEDIUM")
            else:
                severities.append("LOW")
    security_risk = str(security_result.get("risk_level", "LOW")).upper()
    if "HIGH" in severities or security_risk == "HIGH": return "HIGH"
    if "MEDIUM" in severities or security_risk == "MEDIUM": return "MEDIUM"
    if "LOW" in severities: return "LOW"
    return "NONE"

def calculate_quality_score(code, static_issues, security_result, language):
    code_str = clean_code(code)
    score = 100

    for issue in static_issues:
        if isinstance(issue, dict):
            severity = str(issue.get("severity", "")).upper()
            if severity == "HIGH": score -= 15
            elif severity == "MEDIUM": score -= 8
            else: score -= 3
        else:
            issue_str = str(issue).lower()
            if any(k in issue_str for k in ("off-by-one", "syntax error", "undefined function", "undefined variable", "unmatched")):
                score -= 15
            elif "possible" in issue_str or "warning" in issue_str:
                score -= 8
            else:
                score -= 5

    risk = str(security_result.get("risk_level", "LOW")).upper()
    if risk == "HIGH": score -= 15
    elif risk == "MEDIUM": score -= 8

    if language == "JavaScript":
        var_count = len(re.findall(r"\bvar\s+", code_str))
        if var_count > 0: score -= min(10, var_count * 2)

    if language in {"JavaScript", "Java", "C", "C++"}:
        console_log_count = len(re.findall(r"\bconsole\.log\s*\(", code_str))
        if console_log_count > 2: score -= min(5, console_log_count)

    long_lines = sum(1 for line in code_str.splitlines() if len(line) > 100)
    if long_lines > 0: score -= min(10, long_lines * 2)

    if len(code_str) > 250 and not re.search(r"\btry\b|\bcatch\b|\bexcept\b|\bfinally\b", code_str):
        score -= 5

    score = max(0, min(100, score))
    return {"overall": score, "readability": score, "code_structure": score, "error_handling": score, "maintainability": score}

def calculate_complexity(code, language):
    code = clean_code(code)
    lines = code.splitlines()
    total_lines = len(lines)
    code_lines = [line for line in lines if line.strip()]
    blank_lines = total_lines - len(code_lines)
    comment_lines = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*")))
    functions, classes, max_nesting = 0, 0, 0
    if language == "Python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): functions += 1
                elif isinstance(node, ast.ClassDef): classes += 1
        except Exception:
            functions = len(re.findall(r"\bdef\s+\w+\s*\(", code))
            classes = len(re.findall(r"\bclass\s+\w+", code))
    else:
        functions = len(re.findall(r"\b\w+\s+\w+\s*\([^;{}]*\)\s*\{", code))
        classes = len(re.findall(r"\bclass\s+\w+", code))

    depth = 0
    for ch in code:
        if ch == "{": depth += 1; max_nesting = max(max_nesting, depth)
        elif ch == "}": depth = max(0, depth - 1)

    max_line_length, long_lines = 0, 0
    for line in lines:
        length = len(line)
        max_line_length = max(max_line_length, length)
        if length > 100: long_lines += 1
    cyclomatic = 1
    for pattern in [r"\bif\b", r"\belif\b", r"\bfor\b", r"\bwhile\b", r"\bcase\b", r"\bcatch\b", r"\band\b", r"\bor\b", r"\?"]:
        try: cyclomatic += len(re.findall(pattern, code, re.IGNORECASE))
        except re.error: pass
    average_length = (sum(len(line) for line in lines) / total_lines if total_lines else 0)
    complexity_level = "LOW" if cyclomatic <= 5 else ("MEDIUM" if cyclomatic <= 10 else "HIGH")
    maintainability = max(0, min(100, 100 - (long_lines * 2) - max(0, cyclomatic - 5) * 3))
    return {"total_lines": total_lines, "code_lines": len(code_lines), "blank_lines": blank_lines, "comment_lines": comment_lines, "functions": functions, "classes": classes, "cyclomatic_complexity": cyclomatic, "maximum_nesting_depth": max_nesting, "long_lines": long_lines, "average_line_length": round(average_length, 2), "complexity_level": complexity_level, "maintainability_index": maintainability}

def build_explanation(language, static_issues, security_result):
    if static_issues:
        first_issue = static_issues[0]
        if isinstance(first_issue, dict):
            message = str(first_issue.get("message", "")).strip()
        else:
            message = str(first_issue).strip()
        if language == "Python" and "expected ':'" in message.lower():
            return "The Python code contains a syntax error because a block statement is missing a colon (:)."
        if "unmatched parentheses" in message.lower():
            return f"The {language} code has unbalanced parentheses — there is an opening '(' without a matching closing ')'."
        if "unmatched curly braces" in message.lower():
            return f"The {language} code has unbalanced curly braces — a '{{' is missing its matching '}}'."
        if "unmatched square brackets" in message.lower():
            return f"The {language} code has unbalanced square brackets — a '[' is missing its matching ']'."
        if "off-by-one" in message.lower():
            return f"The {language} code contains an off-by-one error in a loop. The loop condition uses '<=' with a length expression, which causes an out-of-bounds access on the final iteration."
        return f"The {language} static analyzer detected {len(static_issues)} issue(s). The main detected issue is: {message}"
    if security_result.get("issues"):
        first_sec = security_result["issues"][0]
        sec_msg = first_sec.get("message", "") if isinstance(first_sec, dict) else str(first_sec)
        return f"The {language} code passed local static analysis, but the security scanner detected potential security-risk patterns. The main issue is: {sec_msg}"
    return f"The {language} code passed the local static and security analysis without detectable issues."

def build_root_cause(static_issues, security_result=None):
    if static_issues:
        messages = []
        for item in static_issues:
            if isinstance(item, dict):
                msg = str(item.get("message", "")).strip()
            else:
                msg = str(item).strip()
            if msg: messages.append(msg)
        if not messages:
            return "No specific root cause was identified."
        first_message = messages[0].lower()
        if "expected ':'" in first_message:
            return "The Python block statement is missing the required colon (:)."
        if "unmatched parentheses" in first_message:
            return "An opening parenthesis '(' was not followed by a matching closing parenthesis ')'."
        if "unmatched curly braces" in first_message:
            return "An opening curly brace '{' was not followed by a matching closing brace '}'."
        if "unmatched square brackets" in first_message:
            return "An opening square bracket '[' was not followed by a matching closing bracket ']'."
        if "off-by-one" in first_message:
            return "The loop uses '<=' against the collection's length, so on the final iteration the index equals the length and accesses an undefined element. The condition should use '<' instead."
        return "The detected problem(s) are caused by: " + " ".join(messages)

    if security_result and security_result.get("issues"):
        first_sec = security_result["issues"][0]
        sec_msg = first_sec.get("message", "") if isinstance(first_sec, dict) else str(first_sec)
        return f"The code contains a security-risk pattern: {sec_msg} This can lead to unintended code execution or data exposure."
    return "No specific root cause was identified because no static analysis issue was detected."

def build_suggested_fixes(static_issues, automatic_fixes, security_result=None, language=None, auto_fix_skipped=False):
    suggestions = []
    for issue in static_issues:
        if isinstance(issue, dict):
            message = str(issue.get("message", ""))
        else:
            message = str(issue)
        lower_message = message.lower()
        if "expected ':'" in lower_message:
            suggestions.append("Add ':' at the end of the Python block statement shown in the error.")
        elif "python syntax error" in lower_message:
            suggestions.append("Correct the Python syntax described in the detected error and run the analyzer again.")
        elif "undefined variable" in lower_message:
            suggestions.append("Define the variable before using it and verify that the variable name is spelled correctly.")
        elif "semicolon" in lower_message:
            suggestions.append("Add the missing semicolon at the indicated line.")
        elif "unmatched parentheses" in lower_message or "unmatched parenthesis" in lower_message:
            suggestions.append("Add the missing closing parenthesis ')' where the opening '(' has no match.")
        elif "unmatched curly braces" in lower_message or "unmatched brace" in lower_message:
            suggestions.append("Add the missing closing curly brace '}' where the opening '{' has no match.")
        elif "unmatched square brackets" in lower_message or "unmatched bracket" in lower_message:
            suggestions.append("Add the missing closing square bracket ']' where the opening '[' has no match.")
        elif "off-by-one" in lower_message:
            suggestions.append("Change '<=' to '<' in the loop condition. Using '<=' against the collection's length causes an out-of-bounds access on the last iteration.")
        elif "html issue" in lower_message and "missing" in lower_message and "closing tag" in lower_message:
            suggestions.append("Add the missing HTML closing tag shown in the error.")
        elif "css" in lower_message and "unmatched" in lower_message:
            suggestions.append("Add the missing closing curly brace '}' in the CSS file.")
        elif "undefined function" in lower_message:
            suggestions.append("Define the function before calling it, or check that the function name is spelled correctly.")
        else:
            suggestions.append(f"Review and correct the detected issue: {message}")

    if auto_fix_skipped and language in {"JavaScript", "Java", "C", "C++", "CSS"}:
        suggestions.append("Automatic brace insertion was skipped because the missing brace is inside a nested block. Please add the missing '}' manually at the location indicated by the indentation.")

    for fix in automatic_fixes:
        automatic_message = f"Automatic fix applied: {fix}"
        if automatic_message not in suggestions:
            suggestions.append(automatic_message)

    if security_result and security_result.get("issues"):
        for sec_issue in security_result["issues"]:
            if isinstance(sec_issue, dict):
                fix_text = sec_issue.get("fix", "")
                if fix_text:
                    security_message = f"Security recommendation: {fix_text}"
                    if security_message not in suggestions:
                        suggestions.append(security_message)

    if not suggestions:
        suggestions.append("No fix required. No detectable issues were found.")
    return suggestions

def build_improvements(code, static_issues, security_result, language):
    improvements = []
    code_str = clean_code(code)

    if not static_issues and not security_result.get("issues"):
        improvements.append("Keep the code modular and maintainable.")
    if security_result.get("issues"):
        improvements.append("Remove hardcoded secrets and avoid unsafe command or code execution patterns.")

    if language == "JavaScript":
        var_count = len(re.findall(r"\bvar\s+", code_str))
        if var_count > 0:
            improvements.append(f"Replace 'var' with 'let' or 'const' ({var_count} occurrence(s) found) for better scoping and safety.")
        console_log = len(re.findall(r"\bconsole\.log\s*\(", code_str))
        if console_log > 1:
            improvements.append("Remove leftover console.log() debugging statements before production use.")

    if len(code_str.splitlines()) > 100:
        improvements.append("Consider splitting large sections into smaller functions.")

    if len(code_str) > 250 and not re.search(r"\btry\b|\bcatch\b|\bexcept\b|\bfinally\b", code_str):
        improvements.append("Add error handling (try/catch) to make the code more robust.")

    if not improvements:
        improvements.append("Improve naming, readability, validation, and error handling where appropriate.")
    return improvements

# ============================================================
# TEST CASE GENERATION
# ============================================================
def _detect_param_type(param_name, body, language):
    name = param_name.lower().strip()
    if name in ("items", "list", "arr", "array", "elements", "values", "collection", "data", "records", "rows", "products", "users", "students", "employees", "orders"):
        if re.search(rf"\b{re.escape(param_name)}\s*\[[^\]]*\]\s*\.", body):
            return "array_of_objects"
        return "array"
    if name in ("name", "text", "message", "title", "str", "string", "word", "sentence", "input", "label", "description"):
        return "string"
    if name in ("count", "num", "number", "amount", "value", "total", "size", "length", "index", "quantity", "price", "rate", "age", "score", "x", "y", "z", "a", "b", "c", "n", "m", "discount"):
        return "number"
    if name in ("flag", "enabled", "isvalid", "is_valid", "active", "done", "success"):
        return "boolean"
    if name in ("config", "options", "settings", "params", "obj", "object", "user", "item", "record"):
        return "object"
    if re.search(rf"\b{re.escape(param_name)}\s*\[[^\]]*\]\s*\.", body):
        return "array_of_objects"
    if re.search(rf"\b{re.escape(param_name)}\s*\[", body):
        return "array"
    if re.search(rf"\b{re.escape(param_name)}\.(toUpperCase|toLowerCase|charAt|slice|substring|split|trim|replace|indexOf|includes|startsWith|endsWith)", body):
        return "string"
    if re.search(rf"\b{re.escape(param_name)}\s*[\+\-\*\/\%]", body) or re.search(rf"[\+\-\*\/\%]\s*{re.escape(param_name)}\b", body):
        return "number"
    if re.search(rf"\blen\s*\(\s*{re.escape(param_name)}\s*\)", body) or re.search(rf"{re.escape(param_name)}\.length", body):
        return "array"
    if re.search(rf"\b{re.escape(param_name)}\.[a-zA-Z_]", body):
        return "object"
    return "unknown"

def _sample_value_for_type(param_type, param_name, variant="typical", lang="JavaScript"):
    if param_type == "number":
        return {"typical": "10", "zero": "0", "negative": "-5", "large": "1000000"}.get(variant, "10")
    if param_type == "string":
        return {"typical": '"hello"', "zero": '""', "negative": '"test"', "large": '"a longer sample string"'}.get(variant, '"hello"')
    if param_type == "boolean":
        return {"typical": "true", "zero": "false", "negative": "false", "large": "true"}.get(variant, "true")
    if param_type == "array":
        return {"typical": "[1, 2, 3]", "zero": "[]", "negative": "[-1, 0, 1]", "large": "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"}.get(variant, "[1, 2, 3]")
    if param_type == "array_of_objects":
        if lang == "Python":
            return {"typical": '[{"name": "Item 1", "price": 9.99, "quantity": 2}]', "zero": "[]", "negative": '[{"name": "Item", "price": -5, "quantity": 1}]', "large": '[{"name": "Item " + str(i), "price": 1.0, "quantity": 1} for i in range(10)]'}.get(variant, '[{"name": "Item 1", "price": 9.99, "quantity": 2}]')
        return {"typical": '[{ name: "Item 1", price: 9.99, quantity: 2 }]', "zero": "[]", "negative": '[{ name: "Item", price: -5, quantity: 1 }]', "large": '[{ name: "Item 1", price: 1, quantity: 1 }, { name: "Item 2", price: 2, quantity: 2 }]'}.get(variant, '[{ name: "Item 1", price: 9.99, quantity: 2 }]')
    if param_type == "object":
        if lang == "Python":
            return {"typical": '{"key": "value"}', "zero": "{}", "negative": '{"key": None}', "large": '{"a": 1, "b": 2, "c": 3, "d": 4}'}.get(variant, '{"key": "value"}')
        return {"typical": '{ key: "value" }', "zero": "{}", "negative": '{ key: null }', "large": '{ a: 1, b: 2, c: 3, d: 4 }'}.get(variant, '{ key: "value" }')
    return {"typical": "10", "zero": "0", "negative": "-5", "large": "1000000"}.get(variant, "10")

def _detect_function_purpose(function_name):
    name = (function_name or "").lower()
    if any(k in name for k in ("calculate", "compute", "sum", "total", "add", "subtract", "multiply", "divide", "average", "mean", "discount")):
        return "math"
    if any(k in name for k in ("format", "render", "display", "print", "show", "stringify")):
        return "format"
    if any(k in name for k in ("validate", "check", "verify", "is", "has", "can")):
        return "validate"
    if any(k in name for k in ("get", "fetch", "load", "read", "query")):
        return "get"
    if any(k in name for k in ("set", "update", "save", "write", "store")):
        return "set"
    if any(k in name for k in ("filter", "find", "search", "sort")):
        return "list"
    if any(k in name for k in ("create", "build", "make", "generate")):
        return "construct"
    return "unknown"

def _clean_param_name(raw_param, language):
    p = raw_param.strip()
    p = p.split("=")[0].strip()
    p = p.split(":")[0].strip()
    if language in {"Java", "C", "C++"}:
        p = p.replace("[]", " ")
        tokens = p.split()
        if tokens: return tokens[-1].strip()
        return p
    return p

def _extract_function_body(code, function_name, language):
    if language == "Python":
        pattern = rf"(?:^|\n)(?:[ \t]*)def\s+{re.escape(function_name)}\s*\([^)]*\)\s*:(.*?)(?=\n(?:[ \t]*def\s|\S|\Z))"
        m = re.search(pattern, code, re.DOTALL)
        if m: return m.group(1)
        return code

    start_pattern = rf"\bfunction\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{"
    m = re.search(start_pattern, code)
    if not m:
        start_pattern = rf"\b[A-Za-z_][A-Za-z0-9_<>\[\]\s\*]*?\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{"
        m = re.search(start_pattern, code)
    if not m:
        start_pattern = rf"\b{re.escape(function_name)}\s*\([^)]*\)\s*\{{"
        m = re.search(start_pattern, code)
    if not m:
        return code

    start_index = m.end() - 1
    depth = 0
    in_string = False
    quote_char = None
    i = start_index
    while i < len(code):
        ch = code[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == quote_char:
                in_string = False
            i += 1
            continue
        if ch in ('"', "'", "`"):
            in_string = True
            quote_char = ch
            i += 1
            continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return code[m.start():i + 1]
        i += 1
    return code[m.start():]

def _extract_clamp_info(name, body, language):
    if language == "Python":
        pattern = rf"if\s+{re.escape(name)}\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)\s*:\s*\n\s*{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)"
    else:
        pattern = rf"if\s*\(\s*{re.escape(name)}\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)\s*\)\s*\{{[^}}]*?{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\s*;"
    m = re.search(pattern, body, re.DOTALL)
    if m:
        return (m.group(1), m.group(2), m.group(3))
    return None

def _resolve_local_assignment(name, body, language):
    if language == "Python":
        first_return_m = re.search(r"^\s*return\b", body, re.MULTILINE)
        if first_return_m:
            body = body[:first_return_m.start()]
        all_assignments = re.findall(rf"^\s*{re.escape(name)}\s*=\s*(.+?)$", body, re.MULTILINE)
    else:
        first_return_m = re.search(r"\breturn\b", body)
        if first_return_m:
            body = body[:first_return_m.start()]
        all_assignments = re.findall(rf"\b{re.escape(name)}\s*=\s*([^;=]+?);", body)

    if not all_assignments:
        return None
    first_expr = all_assignments[0].strip()
    if len(all_assignments) == 1:
        return first_expr
    subsequent = [a.strip() for a in all_assignments[1:]]
    all_numeric = all(re.match(r"^-?\d+(\.\d+)?$", s) for s in subsequent)
    if all_numeric:
        return first_expr
    return None

def _resolve_conditional_assignment(name, body, language):
    if language == "Python":
        first_return_m = re.search(r"^\s*return\b", body, re.MULTILINE)
        if first_return_m:
            body = body[:first_return_m.start()]
        base_m = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+?)$", body, re.MULTILINE)
        if not base_m: return None
        base_expr = base_m.group(1).strip()
        cond_m = re.search(
            rf"if\s+{re.escape(name)}\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)\s*:\s*\n"
            rf"\s*{re.escape(name)}\s*=\s*(.+?)$",
            body, re.MULTILINE
        )
        else_m = re.search(rf"else\s*:\s*\n\s*{re.escape(name)}\s*=\s*(.+?)$", body, re.MULTILINE)
        if cond_m and else_m:
            return {"base": base_expr, "op": cond_m.group(1), "threshold": cond_m.group(2),
                    "then_expr": cond_m.group(3).strip(), "else_expr": else_m.group(1).strip()}
    else:
        first_return_m = re.search(r"\breturn\b", body)
        if first_return_m:
            body = body[:first_return_m.start()]
        base_m = re.search(rf"\b{re.escape(name)}\s*=\s*([^;=]+?);", body)
        if not base_m: return None
        base_expr = base_m.group(1).strip()

        if_else_m = re.search(
            rf"if\s*\(\s*{re.escape(name)}\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)\s*\)\s*\{{"
            rf"[^}}]*?{re.escape(name)}\s*=\s*([^;]+?)\s*;"
            rf"[^}}]*?\}}?\s*else\s*\{{"
            rf"[^}}]*?{re.escape(name)}\s*=\s*([^;]+?)\s*;",
            body, re.DOTALL
        )
        if if_else_m:
            return {"base": base_expr, "op": if_else_m.group(1), "threshold": if_else_m.group(2),
                    "then_expr": if_else_m.group(3).strip(), "else_expr": if_else_m.group(4).strip()}
    return None

def _is_safe_expression(expr):
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_\s\+\-\*\/\%\(\)\.]*$", expr):
        return False
    if re.search(r"[A-Za-z_][A-Za-z0-9_]*\s*\(", expr):
        return False
    if "." in expr:
        for token in re.findall(r"[A-Za-z0-9_\.]+", expr):
            if "." in token and not re.match(r"^\d+\.\d+$", token):
                return False
    if re.search(r"[\[\]\{\}\,]", expr): return False
    if re.search(r"\b(True|False|None|null|true|false|and|or|not)\b", expr): return False
    if re.search(r"==|!=|<=|>=|<|>|&&|\|\|", expr): return False
    if re.search(r"[\'\"]", expr): return False
    return True

def _resolve_return_for_eval(body, language):
    if language == "Python":
        returns = re.findall(r"\breturn\s+([^\n]+)", body)
    else:
        returns = re.findall(r"\breturn\s+([^;\n}]+)", body)
    if not returns:
        return {"type": "none"}
    expr = returns[0].strip().rstrip(";").strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", expr):
        if _is_safe_expression(expr):
            return {"type": "simple", "expr": expr}
        return {"type": "none"}
    simple = _resolve_local_assignment(expr, body, language)
    if simple and _is_safe_expression(simple):
        return {"type": "simple", "expr": simple}
    cond = _resolve_conditional_assignment(expr, body, language)
    if cond:
        if _is_safe_expression(cond["base"]) and _is_safe_expression(cond["then_expr"]) and _is_safe_expression(cond["else_expr"]):
            return {"type": "conditional", "name": expr, **cond}
    return {"type": "none"}

def _safe_eval_expression(expr, param_values):
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return False, "parse error"
    allowed_node_types = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_node_types):
            return False, f"unsupported node: {type(node).__name__}"
        if isinstance(node, (ast.Call, ast.Attribute, ast.Subscript, ast.Lambda, ast.Dict, ast.List, ast.Set, ast.Tuple, ast.comprehension)):
            return False, "unsupported construct"
    def _eval(node):
        if isinstance(node, ast.Expression): return _eval(node.body)
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name):
            if node.id in param_values: return param_values[node.id]
            raise NameError(f"unknown name: {node.id}")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left); right = _eval(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
            if isinstance(node.op, ast.Mod): return left % right
            if isinstance(node.op, ast.Pow): return left ** right
            raise ValueError("unsupported binary operator")
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.USub): return -operand
            if isinstance(node.op, ast.UAdd): return +operand
            raise ValueError("unsupported unary operator")
        raise ValueError(f"unsupported node: {type(node).__name__}")
    try:
        return True, _eval(tree)
    except ZeroDivisionError:
        return False, "division by zero"
    except Exception as e:
        return False, str(e)

def _variant_python_value_for_param(param_type, variant):
    if param_type == "number":
        return {"typical": 10, "zero": 0, "negative": -5, "large": 1000000}.get(variant, 10)
    if param_type == "string":
        return {"typical": "hello", "zero": "", "negative": "test", "large": "a longer sample string"}.get(variant, "hello")
    if param_type == "boolean":
        return {"typical": True, "zero": False, "negative": False, "large": True}.get(variant, True)
    return None

def _apply_clamp_if_needed(base_num, clamp_info):
    if not clamp_info:
        return base_num, False
    op, threshold_str, override_str = clamp_info
    try:
        threshold = float(threshold_str)
        override = float(override_str)
    except (ValueError, TypeError):
        return base_num, False
    triggers = False
    if op == "<" and base_num < threshold: triggers = True
    elif op == "<=" and base_num <= threshold: triggers = True
    elif op == ">" and base_num > threshold: triggers = True
    elif op == ">=" and base_num >= threshold: triggers = True
    elif op == "==" and base_num == threshold: triggers = True
    if triggers:
        return override, True
    return base_num, False

def _compute_expected_output(return_resolution, params, param_types, variant, language, clamp_info=None):
    for ptype in param_types:
        if ptype not in {"number", "string", "boolean", "unknown"}:
            return False, None
    values = {}
    for pname, ptype in zip(params, param_types):
        if ptype == "unknown":
            ptype = "number"
        v = _variant_python_value_for_param(ptype, variant)
        if v is None:
            return False, None
        values[pname] = v

    if not return_resolution or return_resolution.get("type") == "none":
        return False, None

    result = None
    if return_resolution["type"] == "simple":
        ok, result = _safe_eval_expression(return_resolution["expr"], values)
        if not ok: return False, None
    elif return_resolution["type"] == "conditional":
        ok, base_val = _safe_eval_expression(return_resolution["base"], values)
        if not ok: return False, None
        op = return_resolution["op"]
        try: threshold = float(return_resolution["threshold"])
        except (ValueError, TypeError): return False, None
        triggered = False
        if isinstance(base_val, (int, float)) and not isinstance(base_val, bool):
            bv = float(base_val)
            if op == "<" and bv < threshold: triggered = True
            elif op == "<=" and bv <= threshold: triggered = True
            elif op == ">" and bv > threshold: triggered = True
            elif op == ">=" and bv >= threshold: triggered = True
            elif op == "==" and bv == threshold: triggered = True
            elif op == "!=" and bv != threshold: triggered = True
        branch_expr = return_resolution["then_expr"] if triggered else return_resolution["else_expr"]
        branch_values = dict(values)
        branch_values[return_resolution["name"]] = base_val
        ok, result = _safe_eval_expression(branch_expr, branch_values)
        if not ok: return False, None
    else:
        return False, None

    if clamp_info and isinstance(result, (int, float)) and not isinstance(result, bool):
        result, _ = _apply_clamp_if_needed(float(result), clamp_info)

    if isinstance(result, bool): return True, "true" if result else "false"
    if isinstance(result, str): return True, f'"{result}"'
    if isinstance(result, float):
        if result.is_integer(): return True, str(int(result))
        return True, f"{result:.4f}".rstrip("0").rstrip(".")
    return True, str(result)

def _extract_function_info(code, language):
    if language == "Python":
        best_match = None
        fallback_match = None
        for m in re.finditer(r"\bdef\s+(\w+)\s*\(([^)]*)\)\s*:", code):
            name = m.group(1)
            if name.startswith("__") and name.endswith("__"): continue
            raw_params = m.group(2)
            params = [_clean_param_name(p, language) for p in raw_params.split(",") if p.strip()]
            if fallback_match is None: fallback_match = (name, params)
            real_params = [p for p in params if p != "self"]
            if real_params:
                best_match = (name, params)
                break
        if best_match is None: best_match = fallback_match
        if best_match is not None:
            name, params = best_match
            body = _extract_function_body(code, name, language)
            return name, params, body
        return None, [], code
    elif language in {"JavaScript", "Java", "C", "C++"}:
        match = re.search(r"\bfunction\s+(\w+)\s*\(([^)]*)\)", code)
        if not match:
            match = re.search(r"\b[A-Za-z_][A-Za-z0-9_<>\[\]\s\*]*?\s+(\w+)\s*\(([^)]*)\)\s*\{", code)
        if match:
            name = match.group(1)
            raw_params = match.group(2)
            params = [_clean_param_name(p, language) for p in raw_params.split(",") if p.strip()]
            body = _extract_function_body(code, name, language)
            return name, params, body
    return None, [], code

def _describe_return_behavior(body, language):
    if not body: return False, None
    if language == "Python":
        returns = re.findall(r"^\s*return\s*(.*)$", body, re.MULTILINE)
    else:
        returns = re.findall(r"\breturn\s+([^;\n}]+)", body)
    if not returns: return False, None
    non_empty = [r.strip().rstrip(";").strip() for r in returns if r.strip()]
    if not non_empty: return True, None
    return True, non_empty[0]

def generate_test_cases(code, language):
    code = clean_code(code)
    language = normalize_language(language)
    function_name, params, body = _extract_function_info(code, language)
    if not function_name or not params:
        return [
            {"name": "Basic Execution", "input": "Sample valid input", "expected_output": "Program completes successfully"},
            {"name": "Boundary Values", "input": "Zero / empty / minimum values", "expected_output": "Program handles boundary values"},
            {"name": "Invalid Input", "input": "Unexpected input", "expected_output": "Program handles invalid input safely"},
        ]
    effective_params = [p for p in params if p != "self"]
    if not effective_params: effective_params = params
    param_types = [_detect_param_type(p, body, language) for p in effective_params]
    purpose = _detect_function_purpose(function_name)
    return_resolution = _resolve_return_for_eval(body, language)

    clamp_info = None
    if return_resolution and return_resolution.get("type") != "none":
        if language == "Python":
            original_returns = re.findall(r"\breturn\s+([^\n]+)", body)
        else:
            original_returns = re.findall(r"\breturn\s+([^;\n}]+)", body)
        if original_returns:
            ret_var = original_returns[0].strip().rstrip(";").strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", ret_var):
                clamp_info = _extract_clamp_info(ret_var, body, language)

    has_return, raw_return = _describe_return_behavior(body, language)
    has_state_mutation = bool(re.search(r"\bself\.[A-Za-z_]\w*\s*(=|\+=|-=|\*=|/=)", body or ""))
    has_method_call = bool(re.search(r"\bself\.[A-Za-z_]\w*\s*\(", body or ""))
    variants = [
        ("typical",  "Typical values"),
        ("zero",     "Boundary: zero or empty"),
        ("negative", "Boundary: negative or unusual"),
        ("large",    "Boundary: large input"),
    ]
    test_cases = []
    for variant_key, variant_name in variants:
        inputs = [_sample_value_for_type(ptype, pname, variant_key, language) for ptype, pname in zip(param_types, effective_params)]
        input_str = ", ".join(inputs)
        expected = None
        if return_resolution and return_resolution.get("type") != "none":
            ok, computed = _compute_expected_output(return_resolution, effective_params, param_types, variant_key, language, clamp_info)
            if ok and computed is not None:
                expected = computed
        if expected is None:
            if not has_return and has_state_mutation:
                expected = "Function executes without error; modifies object state (returns nothing)"
                if param_types and param_types[0] != "unknown":
                    expected += f" — input type: {param_types[0].replace('_', ' ')}"
            elif not has_return and has_method_call:
                expected = "Function executes without error; produces side effects (returns nothing)"
                if param_types and param_types[0] != "unknown":
                    expected += f" — input type: {param_types[0].replace('_', ' ')}"
            elif not has_return:
                expected = "Function executes without error (returns nothing)"
                if param_types and param_types[0] != "unknown":
                    expected += f" — input type: {param_types[0].replace('_', ' ')}"
            else:
                if purpose == "math": expected = "Numeric result based on the function's arithmetic logic"
                elif purpose == "validate": expected = "true/false — whether the input satisfies the validation rule"
                elif purpose == "format": expected = "Formatted string representation of the input"
                elif purpose == "get": expected = "The requested value or resource"
                elif purpose == "set": expected = "Confirmation that the value was updated"
                elif purpose == "list": expected = "Filtered, sorted, or searched result"
                elif purpose == "construct": expected = "Newly created object or value"
                else: expected = "Result computed by the function"
                if param_types and param_types[0] != "unknown":
                    expected += f" (input type: {param_types[0].replace('_', ' ')})"
        test_cases.append({
            "name": variant_name,
            "input": f"{function_name}({input_str})",
            "expected_output": expected,
        })
    return test_cases

# ============================================================
# OLLAMA AI ANALYSIS
# ============================================================
def run_ollama_analysis(code, language, static_issues, security_result):
    if not ENABLE_OLLAMA: return {"enabled": False, "success": False, "message": "Ollama AI analysis is disabled."}
    if not code: return {"enabled": True, "success": False, "message": "No code was provided."}
    code_for_ai = code[:MAX_AI_CODE_LENGTH]
    static_text = "None"
    if isinstance(static_issues, list) and static_issues:
        static_text = "\n".join([f"- {i['message']} (Severity: {i['severity']})" for i in static_issues if isinstance(i, dict)])
    security_text = "None"
    if isinstance(security_result, dict) and security_result.get("issues"):
        security_text = "\n".join([f"- {i['message']} (Severity: {i['severity']})" for i in security_result["issues"] if isinstance(i, dict)])
    prompt = f"""You are an AI software code analyzer.
Programming language: {language}
The local static analyzer has ALREADY found the following issues in this code:
{static_text}
The local security scanner found:
{security_text}
YOUR TASK: Analyze the code and provide: Bug, Severity, Explanation, Root Cause, Suggested Fix, Corrected Code, Improvements.
IMPORTANT RULES:
- The local static analyzer result is AUTHORITATIVE.
- If the static analyzer found no issues, do not invent bugs.
- Keep the response concise.
CODE:
{code_for_ai}"""
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"num_predict": OLLAMA_MAX_TOKENS}}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return {"enabled": True, "success": True, "response": response.json().get("response", "")}
    except Exception as exc:
        return {"enabled": True, "success": False, "message": str(exc)}

# ============================================================
# MAIN ANALYSIS
# ============================================================
def analyze_code(code, language="Python"):
    code = clean_code(code)
    language = normalize_language(language)
    if not code.strip(): return {"success": False, "error": "No code was provided."}
    if len(code) > MAX_AI_CODE_LENGTH: return {"success": False, "error": f"Code is too long. Maximum allowed length is {MAX_AI_CODE_LENGTH} characters."}

    static_result = run_static_analysis(code, language)
    if isinstance(static_result, dict):
        static_issues = static_result.get("issues", [])
    elif isinstance(static_result, list):
        static_issues = static_result
    else:
        static_issues = []

    security_result = security_scan(code, language)
    if not isinstance(security_result, dict):
        security_result = {"risk_level": "LOW", "issues": [], "message": "Security scan returned invalid data."}

    corrected_code, automatic_fixes = apply_automatic_fixes(code, language)
    code_was_changed = corrected_code.strip() != code.strip()

    post_fix_static = run_static_analysis(corrected_code, language)
    if isinstance(post_fix_static, dict):
        post_fix_static_issues = post_fix_static.get("issues", [])
    elif isinstance(post_fix_static, list):
        post_fix_static_issues = post_fix_static
    else:
        post_fix_static_issues = []

    auto_fix_skipped = False
    if language in {"JavaScript", "Java", "C", "C++", "CSS"}:
        original_open = code.count("{")
        original_close = code.count("}")
        corrected_open = corrected_code.count("{")
        corrected_close = corrected_code.count("}")
        if original_open != original_close and corrected_open != corrected_close:
            auto_fix_skipped = True

    post_fix_security = security_scan(corrected_code, language)
    if not isinstance(post_fix_security, dict):
        post_fix_security = {"risk_level": "LOW", "issues": [], "message": "Security scan returned invalid data."}

    severity = calculate_severity(static_issues, security_result)
    quality_score = calculate_quality_score(code, static_issues, security_result, language)
    complexity = calculate_complexity(code, language)
    explanation = build_explanation(language, static_issues, security_result)
    root_cause = build_root_cause(static_issues, security_result)
    suggested_fixes = build_suggested_fixes(static_issues, automatic_fixes, security_result, language, auto_fix_skipped)
    improvements = build_improvements(code, static_issues, security_result, language)
    test_cases = generate_test_cases(code, language)
    ai_analysis = run_ollama_analysis(code, language, static_issues, security_result)

    if auto_fix_skipped and code_was_changed:
        fix_status = "partial"
    elif auto_fix_skipped:
        fix_status = "skipped"
    elif code_was_changed:
        fix_status = "applied"
    else:
        fix_status = "none"

    warnings = []
    if auto_fix_skipped and code_was_changed:
        warnings.append("Some issues were auto-fixed, but the missing nested brace could not be safely auto-fixed. Please review the corrected code and apply the remaining fix manually.")
    elif auto_fix_skipped:
        warnings.append("The 'Corrected Code' section below shows your ORIGINAL code unchanged. Automatic fixing was not possible because the missing brace is in a nested block. Please apply the fix manually.")
    elif code_was_changed:
        warnings.append("Automatic corrections were applied to the generated corrected code.")

    if not static_issues and not auto_fix_skipped:
        warnings.append("No static analysis issues were detected.")

    if auto_fix_skipped:
        post_fix_static_report = "Some issues could not be auto-fixed. Please review the ORIGINAL static analysis and apply the recommended fixes manually."
    elif code_was_changed:
        if not post_fix_static_issues:
            if language in {"C", "C++", "Java", "JavaScript", "CSS"}:
                post_fix_static_report = "Braces/brackets are now balanced. Please verify the corrected code manually before use."
            else:
                post_fix_static_report = "The automatic fix was applied. Please verify the corrected code manually before use."
        else:
            post_fix_static_report = post_fix_static_issues
    elif static_issues:
        post_fix_static_report = (
            "No automatic fix was applied. The original issues remain — "
            "please review the ORIGINAL static analysis section and fix manually."
        )
    else:
        post_fix_static_report = "No static analysis issues detected."

    original_sec_titles = set()
    for s in security_result.get("issues", []):
        if isinstance(s, dict):
            t = s.get("title") or s.get("message", "")
            if t: original_sec_titles.add(str(t).strip())
    remaining_sec_titles = set()
    for s in post_fix_security.get("issues", []):
        if isinstance(s, dict):
            t = s.get("title") or s.get("message", "")
            if t: remaining_sec_titles.add(str(t).strip())
    unchanged_security = original_sec_titles & remaining_sec_titles
    if unchanged_security:
        warnings.append(f"{len(unchanged_security)} security issue(s) require manual review. The auto-fix engine does not modify security-sensitive patterns like eval() — see the SECURITY ANALYSIS section for the recommended fix for each issue.")

    bug_detected = (
        static_issues[0].get("message", "Static analysis issue detected.")
        if (static_issues and isinstance(static_issues[0], dict))
        else (static_issues[0] if static_issues
              else ("Security-risk pattern detected." if security_result.get("issues") else "No static analysis issues detected."))
    )

    return {
        "success": True, "language": language, "programming_language": language,
        "code": code, "corrected_code": corrected_code,
        "fix_status": fix_status,
        "bug": bug_detected, "bug_detected": bug_detected,
        "issues": static_issues, "static_analysis": static_issues,
        "security_issues": security_result.get("issues", []),
        "security_risk": security_result.get("risk_level", "LOW"),
        "security": security_result,
        "severity": severity, "quality_score": quality_score,
        "complexity": complexity, "complexity_analysis": complexity, "metrics": complexity,
        "explanation": explanation, "root_cause": root_cause,
        "suggested_fix": (suggested_fixes[0] if suggested_fixes else "No fix required."),
        "suggested_fixes": suggested_fixes,
        "automatic_fixes": automatic_fixes, "test_cases": test_cases, "improvements": improvements,
        "post_fix_static_analysis": post_fix_static_report,
        "post_fix_analysis": post_fix_static_report,
        "postFixAnalysis": post_fix_static_report,
        "post_fix_security_analysis": post_fix_security,
        "warnings": warnings, "ai_analysis": ai_analysis, "analysis_completed": True
    }
