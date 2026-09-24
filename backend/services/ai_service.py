import ast
import builtins
import difflib
import os
import re
import subprocess
import symtable
import tempfile
import time
import shutil
from html.parser import HTMLParser

from services.static_analyzer import run_static_analysis

try:
    from .advanced_analyzer import run_advanced_analysis
except ImportError:
    from services.advanced_analyzer import run_advanced_analysis


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate",
)
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MAX_AI_CODE_LENGTH = 15000

ENABLE_CODE_EXECUTION = os.getenv(
    "ENABLE_CODE_EXECUTION",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}

CODE_EXECUTION_TIMEOUT = int(
    os.getenv("CODE_EXECUTION_TIMEOUT", "5")
)

CODE_EXECUTION_MAX_OUTPUT = 4000

ENABLE_OLLAMA = os.getenv(
    "ENABLE_OLLAMA",
    "false",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "25"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "800"))

PYTHON_BUILTINS = set(dir(builtins))


SEMANTIC_VARIABLE_ALIASES = {
    "count": ["quantity", "number", "total", "amount", "num", "qty"],
    "amount": ["quantity", "count", "total", "price", "value", "sum"],
    "quantity": ["count", "amount", "number", "total", "qty", "num"],
    "qty": ["quantity", "count", "amount", "number"],
    "number": ["count", "amount", "quantity", "num", "total"],
    "num": ["number", "count", "amount", "quantity", "total"],
    "total": ["sum", "amount", "count", "quantity", "number"],
    "sum": ["total", "amount", "count", "quantity"],
    "value": ["amount", "price", "val", "total"],
    "price": ["amount", "value", "cost", "rate"],
    "cost": ["price", "amount", "value", "rate"],
    "rate": ["price", "cost", "value", "ratio"],
    "length": ["len", "size", "count", "total"],
    "len": ["length", "size", "count"],
    "size": ["length", "len", "count"],
    "index": ["i", "idx", "indx", "position", "pos"],
    "idx": ["index", "i", "position", "pos"],
    "i": ["index", "idx", "counter"],
    "quanity": ["quantity", "count", "amount"],
    "quanitity": ["quantity", "count", "amount"],
    "lenght": ["length", "len", "size"],
    "indx": ["index", "idx", "i"],
    "adress": ["address"],
    "recieve": ["receive"],
    "seperate": ["separate"],
}


JS_COMMON_TYPO_FIXES = {
    "lenght": "length",
    "lenghts": "lengths",
    "widht": "width",
    "widhts": "widths",
    "heigth": "height",
    "heigths": "heights",
    "functon": "function",
    "fucntion": "function",
    "funtion": "function",
    "retrun": "return",
    "reutrn": "return",
    "indx": "index",
    "indxe": "index",
    "adress": "address",
    "adresss": "address",
    "recieve": "receive",
    "recieved": "received",
    "seperate": "separate",
    "seperated": "separated",
    "sucess": "success",
    "sucessful": "successful",
    "defualt": "default",
    "acheive": "achieve",
    "occured": "occurred",
    "referer": "referrer",
    "enviroment": "environment",
    "enviornment": "environment",
    "paramter": "parameter",
    "paramters": "parameters",
    "arguement": "argument",
    "arguements": "arguments",
    "docuemnt": "document",
    "consle": "console",
    "consoel": "console",
    "retun": "return",
    "valeu": "value",
    "vaue": "value",
    "nulll": "null",
    "undefind": "undefined",
    "undefiend": "undefined",
    "nuber": "number",
    "numbr": "number",
    "stirng": "string",
    "strng": "string",
    "arrray": "array",
    "aray": "array",
    "objet": "object",
    "objct": "object",
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_static_issues(result):
    if result is None:
        return []

    if isinstance(result, dict):
        result = result.get("issues", [])

    if isinstance(result, str):
        return list(dict.fromkeys(
            line.strip()
            for line in result.splitlines()
            if line.strip()
        ))

    if isinstance(result, (list, tuple, set)):
        out = []
        for item in result:
            if isinstance(item, dict):
                out.extend(normalize_static_issues(item))
            elif item is not None and str(item).strip():
                out.append(str(item).strip())
        return list(dict.fromkeys(out))

    text = str(result).strip()
    return [text] if text else []


def build_static_analysis(static_issues):
    issues = normalize_static_issues(static_issues)
    return "\n".join(issues) if issues else "No static analysis issues detected."


def normalize_severity(severity):
    match = re.search(
        r"\b(CRITICAL|HIGH|MEDIUM|LOW|NONE)\b",
        str(severity or "NONE").upper(),
    )
    return match.group(1) if match else "MEDIUM"


def is_valid_python_code(code):
    try:
        compile(code, "<submitted_code>", "exec")
        return True
    except SyntaxError:
        return False


def clean_corrected_code(code):
    if not code:
        return ""

    text = str(code).strip()

    fenced = re.search(
        r"```(?:python|py|javascript|js|typescript|ts|java|c\+\+|cpp|c|html|css)?\s*(.*?)```",
        text,
        flags=re.I | re.S,
    )

    if fenced:
        text = fenced.group(1).strip()

    headings = {
        "BUG DETECTED:",
        "SEVERITY:",
        "EXPLANATION:",
        "ROOT CAUSE:",
        "SUGGESTED FIX:",
        "CORRECTED CODE:",
        "IMPROVEMENTS:",
        "STATIC ANALYSIS:",
    }

    return "\n".join(
        line for line in text.splitlines()
        if line.strip().upper() not in headings
    ).strip()


def extract_undefined_variable(static_issues):
    patterns = [
        r"undefined\s+name\s+['\"]([^'\"]+)['\"]",
        r"undefined\s+variable\s*[:\-]?\s*['\"]([^'\"]+)['\"]",
        r"variable\s+['\"]([^'\"]+)['\"]\s+is\s+not\s+defined",
        r"name\s+['\"]([^'\"]+)['\"]\s+is\s+not\s+defined",
    ]

    for issue in normalize_static_issues(static_issues):
        for pattern in patterns:
            match = re.search(pattern, issue, re.I)
            if match:
                return match.group(1)

    return ""


def extract_js_undefined_variable(static_issues):
    for issue in normalize_static_issues(static_issues):
        match = re.search(
            r"ReferenceError:\s*([A-Za-z_$][A-Za-z0-9_$]*)\s+is\s+not\s+defined",
            issue,
        )
        if match:
            return match.group(1)

        match = re.search(
            r"ReferenceError:\s*Cannot\s+access\s+'([A-Za-z_$][A-Za-z0-9_$]*)'\s+before\s+initialization",
            issue,
        )
        if match:
            return match.group(1)

    return ""


def has_serious_static_issue(static_issues):
    serious = (
        "undefined variable",
        "undefined name",
        "syntax error",
        "parsing error",
        "missing closing",
        "unexpected closing",
        "mismatched",
        "invalid syntax",
        "indentation error",
        "invalid indentation",
        "execution check failed",
        "compile error",
        "runtime error",
        "referenceerror",
        "syntaxerror",
        "uninitialized",
        "division by zero",
        "arithmeticexception",
        "zerodivision",
    )

    return any(
        any(word in issue.lower() for word in serious)
        for issue in normalize_static_issues(static_issues)
    )


def _has_wildcard_import(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return bool(
            re.search(
                r"^\s*from\s+[\w.]+\s+import\s+\*",
                code,
                re.M,
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    return True

    return False


# ============================================================
# MULTI-LANGUAGE LOCAL EXECUTION / VALIDATION
# ============================================================

LANGUAGE_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "c++": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "cs": "csharp",
    "c#": "csharp",
    "golang": "go",
    "rs": "rust",
    "kt": "kotlin",
    "rb": "ruby",
    "html5": "html",
    "css3": "css",
    "c/c++": "cpp",
    "ts": "typescript",
}


SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "java",
    "c",
    "cpp",
    "html",
    "css",
}


def canonical_language(language):
    value = str(language or "").strip().lower()
    return LANGUAGE_ALIASES.get(value, value)


def _clip_output(text):
    text = str(text or "")
    if len(text) <= CODE_EXECUTION_MAX_OUTPUT:
        return text
    return text[:CODE_EXECUTION_MAX_OUTPUT] + "\n...[output truncated]"


def _run_process(command, cwd, timeout=CODE_EXECUTION_TIMEOUT):
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

        return {
            "returncode": completed.returncode,
            "stdout": _clip_output(completed.stdout),
            "stderr": _clip_output(completed.stderr),
            "timed_out": False,
        }

    except subprocess.TimeoutExpired as error:
        return {
            "returncode": -1,
            "stdout": _clip_output(error.stdout or ""),
            "stderr": _clip_output(error.stderr or ""),
            "timed_out": True,
        }

    except OSError as error:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(error),
            "timed_out": False,
        }


def _tool_available(name):
    return shutil.which(name) is not None


# ============================================================
# HTML VALIDATION
# ============================================================

class _HTMLValidationParser(HTMLParser):

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img",
        "input", "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Unexpected closing tag </{tag}>.")
            return
        self.stack.pop()


def _validate_html(code):
    parser = _HTMLValidationParser()

    try:
        parser.feed(code)
        parser.close()
    except Exception as error:
        parser.errors.append(str(error))

    if parser.stack:
        parser.errors.append(
            "Unclosed HTML tag(s): " + ", ".join(parser.stack[-10:])
        )

    if parser.errors:
        return {
            "supported": True,
            "status": "validation_error",
            "error_type": "HTMLValidationError",
            "stdout": "",
            "stderr": "\n".join(parser.errors),
            "returncode": 1,
        }

    return {
        "supported": True,
        "status": "success",
        "error_type": None,
        "stdout": "HTML structure validation passed.",
        "stderr": "",
        "returncode": 0,
    }


def fix_html_structure(code):
    if not code:
        return code, ""

    void_tags = {
        "area", "base", "br", "col", "embed", "hr", "img",
        "input", "link", "meta", "param", "source", "track", "wbr",
    }

    tag_pattern = re.compile(
        r"<!--.*?-->|<!DOCTYPE[^>]*>|</?[A-Za-z][^>]*>",
        flags=re.I | re.S,
    )

    stack = []
    output = []
    changed = False
    messages = []
    position = 0

    for match in tag_pattern.finditer(code):
        output.append(code[position:match.start()])
        token = match.group(0)
        position = match.end()

        if token.startswith("<!--") or re.match(r"<!DOCTYPE", token, re.I):
            output.append(token)
            continue

        end_match = re.match(
            r"</\s*([A-Za-z][A-Za-z0-9:-]*)\s*>", token, re.I,
        )
        start_match = re.match(
            r"<\s*([A-Za-z][A-Za-z0-9:-]*)\b[^>]*?>", token, re.I | re.S,
        )

        if end_match:
            tag = end_match.group(1).lower()
            if tag in void_tags:
                output.append(token)
                continue
            if stack and stack[-1] == tag:
                output.append(token)
                stack.pop()
                continue
            if tag in stack:
                while stack and stack[-1] != tag:
                    missing = stack.pop()
                    output.append(f"</{missing}>")
                    changed = True
                    messages.append(
                        f"Added missing </{missing}> before </{tag}>."
                    )
                if stack and stack[-1] == tag:
                    stack.pop()
                output.append(token)
                continue
            changed = True
            messages.append(f"Removed unexpected closing tag </{tag}>.")
            continue

        if start_match:
            tag = start_match.group(1).lower()
            output.append(token)
            self_closing = token.rstrip().endswith("/>")
            if tag not in void_tags and not self_closing:
                stack.append(tag)
            continue

        output.append(token)

    output.append(code[position:])

    while stack:
        tag = stack.pop()
        output.append(f"</{tag}>")
        changed = True
        messages.append(
            f"Added missing </{tag}> at the end of the document."
        )

    corrected = "".join(output)
    if not changed:
        return code, ""
    return corrected, " ".join(dict.fromkeys(messages))


# ============================================================
# CSS VALIDATION
# ============================================================

def _css_scan(code):
    in_string = None
    escaped = False
    depth = 0
    unexpected = []

    i = 0
    length = len(code)

    while i < length:
        if code.startswith("/*", i):
            end = code.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue

        char = code[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if char == "\\" and in_string:
            escaped = True
            i += 1
            continue
        if char in {"'", '"'}:
            if in_string == char:
                in_string = None
            elif in_string is None:
                in_string = char
            i += 1
            continue
        if in_string:
            i += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                unexpected.append(i)
                depth = 0
        i += 1

    return depth, in_string, escaped, unexpected


def _validate_css(code):
    depth, in_string, _escaped, unexpected = _css_scan(code)

    if unexpected:
        return {
            "supported": True,
            "status": "validation_error",
            "error_type": "CSSValidationError",
            "stdout": "",
            "stderr": "Unexpected closing brace '}'.",
            "returncode": 1,
        }

    if in_string or depth != 0:
        return {
            "supported": True,
            "status": "validation_error",
            "error_type": "CSSValidationError",
            "stdout": "",
            "stderr": "Unclosed CSS string or brace detected.",
            "returncode": 1,
        }

    return {
        "supported": True,
        "status": "success",
        "error_type": None,
        "stdout": "CSS structure validation passed.",
        "stderr": "",
        "returncode": 0,
    }


def _looks_like_selector(text):
    text = text.strip()
    if not text:
        return True

    first = text[0]
    if first in ".#@%[:*>+~":
        return True
    if re.match(r"^[a-zA-Z][\w-]*$", text):
        return True

    match = re.match(r"^([a-zA-Z][\w-]*)([.#\[:])", text)
    if match:
        separator = text[match.end() - 1]
        rest = text[match.end():]
        if separator == ":":
            if not rest or rest[0].isspace():
                return False
            if "(" in rest or ")" in rest:
                return False
        return True

    return False


def fix_css_structure(code):
    if not code:
        return code, ""

    messages = []
    insertions = []
    depth = 0
    in_string = None
    escaped = False
    i = 0
    n = len(code)
    buffer_start = 0
    inserted_count = 0

    while i < n:
        if code.startswith("/*", i):
            end = code.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue

        char = code[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if char == "\\" and in_string:
            escaped = True
            i += 1
            continue
        if char in {"'", '"'}:
            if in_string == char:
                in_string = None
            elif in_string is None:
                in_string = char
            i += 1
            continue
        if in_string:
            i += 1
            continue
        if char == "{":
            effective_depth = depth - inserted_count
            if effective_depth >= 1:
                prefix = code[buffer_start:i]
                prefix = re.sub(
                    r"/\*.*?\*/", "", prefix, flags=re.DOTALL,
                )
                if _looks_like_selector(prefix):
                    insertions.append((buffer_start, "\n}"))
                    inserted_count += 1
                    messages.append(
                        "Closed an unclosed CSS rule before a new "
                        "selector."
                    )
            depth += 1
            buffer_start = i + 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                depth = 0
            buffer_start = i + 1
        elif char == ";":
            buffer_start = i + 1
        i += 1

    if in_string:
        return (
            code,
            "An unclosed CSS string requires manual review.",
        )

    if insertions:
        for pos, text in sorted(insertions, key=lambda x: -x[0]):
            code = code[:pos] + text + code[pos:]

    depth, in_string, _escaped, unexpected = _css_scan(code)

    if in_string:
        return (
            code,
            "CSS auto-fix could not resolve the structure safely; "
            "an unclosed string remains.",
        )

    if unexpected:
        chars = list(code)
        for index in reversed(unexpected):
            if 0 <= index < len(chars) and chars[index] == "}":
                del chars[index]

        code = "".join(chars)
        messages.append(
            f"Removed {len(unexpected)} unexpected closing CSS brace"
            f"{'s' if len(unexpected) != 1 else ''}."
        )

        depth, in_string, _escaped, unexpected_after = _css_scan(code)
        if in_string or unexpected_after:
            return (
                code,
                "CSS auto-fix could not safely resolve nested "
                "unmatched braces; manual review required.",
            )

    if depth > 0:
        code = code.rstrip() + "\n" + ("}" * depth)
        messages.append(
            f"Added {depth} missing CSS closing brace"
            f"{'s' if depth != 1 else ''}."
        )

    if not messages:
        return code, ""

    return code, " ".join(dict.fromkeys(messages))


# ============================================================
# JAVA / C / C++ / JAVASCRIPT STATIC RUNTIME DETECTION
# ============================================================

def _compiled_division_by_zero(code, language):
    language = canonical_language(language)

    if language not in {"c", "cpp"}:
        return None

    direct_pattern = re.compile(
        r"(?P<left>[A-Za-z0-9_][A-Za-z0-9_()\[\].]*)"
        r"\s*(?P<op>/|%)\s*0(?![0-9.])"
    )

    direct_match = direct_pattern.search(code)

    if direct_match:
        operator = direct_match.group("op")
        line = code[:direct_match.start()].count("\n") + 1

        return {
            "detected": True,
            "error_type": "DivisionByZero",
            "line": line,
            "bug": (
                f"Division by zero: '{operator}' uses zero as the divisor "
                f"on line {line}."
            ),
            "explanation": (
                "The submitted code performs integer division or modulo "
                "using zero. This can cause a runtime error or undefined "
                "behavior."
            ),
            "root_cause": "The divisor is statically known to be zero.",
            "suggested_fix": (
                "Check the divisor before performing the division or modulo "
                "operation."
            ),
        }

    zero_variables = set(
        re.findall(
            r"\b(?:int|long|short|byte|float|double|"
            r"signed|unsigned)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*0\s*;",
            code,
            flags=re.I,
        )
    )

    zero_variables.update(
        re.findall(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*0\s*;",
            code,
        )
    )

    for variable in zero_variables:
        pattern = re.compile(
            rf"(?P<left>[A-Za-z_][A-Za-z0-9_()\[\].]*)"
            rf"\s*(?P<op>/|%)\s*{re.escape(variable)}\b"
        )

        match = pattern.search(code)

        if match:
            operator = match.group("op")
            line = code[:match.start()].count("\n") + 1

            return {
                "detected": True,
                "error_type": "DivisionByZero",
                "line": line,
                "variable": variable,
                "bug": (
                    f"Division by zero: variable '{variable}' is assigned "
                    f"zero and then used as a divisor on line {line}."
                ),
                "explanation": (
                    f"The divisor variable '{variable}' is statically known "
                    "to contain zero when the division is performed."
                ),
                "root_cause": (
                    f"Variable '{variable}' has value zero before the "
                    "division or modulo operation."
                ),
                "suggested_fix": (
                    f"Validate '{variable}' before using it as a divisor."
                ),
            }

    return None


def _extract_c_function_definitions(code):
    """
    Extract function definitions with their parameter lists and bodies.
    Works for C, C++, and Java-ish syntax.

    Returns list of dicts:
        {
            "name": "divide",
            "params": ["a", "b"],
            "body": "return a / b;",
            "line": 4
        }
    """
    results = []

    func_pattern = re.compile(
        r"\b[A-Za-z_][A-Za-z0-9_<>\[\]:,\s\*&]*?\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"\(([^)]*)\)\s*"
        r"(?:const\s*)?"
        r"\{",
        re.MULTILINE,
    )

    for match in func_pattern.finditer(code):
        name = match.group(1)

        # Skip keywords that aren't really function names
        if name in {
            "if", "while", "for", "switch", "catch", "return",
        }:
            continue

        params_text = match.group(2)

        params = []
        for raw in params_text.split(","):
            raw = raw.strip()
            if not raw:
                continue

            # Drop default value
            raw = raw.split("=")[0].strip()
            # Drop array suffix
            raw = raw.replace("[]", " ").strip()
            # Take last identifier
            tokens = raw.split()
            if tokens:
                pname = tokens[-1].strip("*&")
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", pname):
                    params.append(pname)

        # Find the body via brace matching
        brace_start = match.end() - 1
        depth = 0
        i = brace_start
        in_string = False
        quote_char = None
        body_end = None

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
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
                i += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    body_end = i
                    break
            i += 1

        if body_end is None:
            continue

        body = code[brace_start + 1:body_end]

        results.append({
            "name": name,
            "params": params,
            "body": body,
            "line": code[:match.start()].count("\n") + 1,
            "def_start": match.start(),
            "def_end": body_end,
        })

    return results


def _c_cpp_division_by_zero_via_call(code, language):
    """
    Detect division by zero that flows from call arguments to parameters.

    Example:
        int divide(int a, int b) { return a / b; }
        divide(10, 0);   // ← parameter b receives 0, used as divisor
    """
    functions = _extract_c_function_definitions(code)

    if not functions:
        return None

    func_map = {f["name"]: f for f in functions}

    # Find all call sites
    call_pattern = re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)"
    )

    for call_match in call_pattern.finditer(code):
        fn_name = call_match.group(1)
        args_text = call_match.group(2)

        if fn_name not in func_map:
            continue

        # Skip if this call is part of the function's own definition
        fn_info = func_map[fn_name]
        if (
            fn_info["def_start"]
            <= call_match.start()
            < fn_info["def_end"]
        ):
            continue

        # Parse arguments
        args = [a.strip() for a in args_text.split(",")]

        if len(args) > len(fn_info["params"]):
            continue

        for i, arg in enumerate(args):
            if i >= len(fn_info["params"]):
                break

            param_name = fn_info["params"][i]

            # Is the argument literally 0?
            is_zero_literal = arg in {
                "0", "0L", "0U", "0UL", "0LL", "0ULL", "0x0",
            }

            # Is the argument a variable we know is 0?
            is_zero_var = False
            if not is_zero_literal and re.match(
                r"^[A-Za-z_][A-Za-z0-9_]*$", arg,
            ):
                var_pattern = re.compile(
                    rf"\b(?:int|long|short|byte|float|double|"
                    rf"signed|unsigned)\s+{re.escape(arg)}\s*=\s*0\s*;"
                )
                if var_pattern.search(code):
                    is_zero_var = True

            if not (is_zero_literal or is_zero_var):
                continue

            # Does the function body use this parameter as a divisor?
            body = fn_info["body"]
            divisor_pattern = re.compile(
                rf"(?P<left>[A-Za-z0-9_][A-Za-z0-9_()\[\].]*)"
                rf"\s*(?P<op>/|%)\s*{re.escape(param_name)}\b"
            )

            if divisor_pattern.search(body):
                call_line = code[:call_match.start()].count("\n") + 1

                return {
                    "detected": True,
                    "error_type": "DivisionByZero",
                    "line": call_line,
                    "variable": param_name,
                    "bug": (
                        f"Division by zero: call to '{fn_name}()' on line "
                        f"{call_line} passes zero to parameter "
                        f"'{param_name}', which is used as a divisor "
                        f"inside '{fn_name}()'."
                    ),
                    "explanation": (
                        f"The function '{fn_name}()' uses parameter "
                        f"'{param_name}' as a divisor. The call site on "
                        f"line {call_line} passes a value that is statically "
                        "known to be zero, so the division will fail at "
                        "runtime."
                    ),
                    "root_cause": (
                        f"Parameter '{param_name}' receives value zero from "
                        f"the call to '{fn_name}()' on line {call_line}."
                    ),
                    "suggested_fix": (
                        f"Validate the argument passed to '{param_name}' "
                        f"before calling '{fn_name}()', or handle the zero "
                        "case inside the function."
                    ),
                }

    return None


def _java_division_by_zero(code):
    int_variables = set(
        re.findall(
            r"\b(?:int|long|short|byte)\s+([A-Za-z_]\w*)\b",
            code,
        )
    )

    int_variables.update(
        re.findall(
            r"\b(?:int|long|short|byte)\s+([A-Za-z_]\w*)\s*=\s*0\s*;",
            code,
        )
    )

    direct_pattern = re.compile(
        r"(?P<left>[A-Za-z0-9_][A-Za-z0-9_()\[\].]*)"
        r"\s*(?P<op>/|%)\s*0(?![0-9.])"
    )

    for match in direct_pattern.finditer(code):
        operator = match.group("op")
        line = code[:match.start()].count("\n") + 1

        return {
            "detected": True,
            "error_type": "DivisionByZero",
            "line": line,
            "bug": (
                f"Java integer division by zero: '{operator}' uses zero "
                f"as the divisor on line {line}. This throws "
                "ArithmeticException at runtime."
            ),
            "explanation": (
                "Integer division or modulo by zero in Java throws "
                "ArithmeticException."
            ),
            "root_cause": "The divisor is statically known to be zero.",
            "suggested_fix": (
                "Check the divisor before performing the operation, "
                "or throw an IllegalArgumentException with a clear message."
            ),
        }

    for variable in int_variables:
        pattern = re.compile(
            rf"(?P<left>[A-Za-z_][A-Za-z0-9_()\[\].]*)"
            rf"\s*(?P<op>/|%)\s*{re.escape(variable)}\b"
        )

        match = pattern.search(code)
        if not match:
            continue

        operator = match.group("op")
        line = code[:match.start()].count("\n") + 1

        return {
            "detected": True,
            "error_type": "DivisionByZero",
            "line": line,
            "variable": variable,
            "bug": (
                f"Java integer division by zero: '{variable}' is an "
                f"integer assigned zero and used as a divisor on line "
                f"{line}. This throws ArithmeticException."
            ),
            "explanation": (
                f"The integer variable '{variable}' is statically known "
                "to contain zero when the division is performed."
            ),
            "root_cause": (
                f"Variable '{variable}' has value zero before the operation."
            ),
            "suggested_fix": (
                f"Validate '{variable}' before using it as a divisor."
            ),
        }

    return None


def _javascript_division_by_zero(code):
    direct_pattern = re.compile(
        r"(?P<left>[A-Za-z0-9_$][A-Za-z0-9_$()\[\].]*)"
        r"\s*(?P<op>/|%)\s*0(?![0-9.])"
    )

    direct_match = direct_pattern.search(code)

    if direct_match:
        operator = direct_match.group("op")
        line = code[:direct_match.start()].count("\n") + 1
        result_value = "Infinity" if operator == "/" else "NaN"

        return {
            "detected": True,
            "error_type": "DivisionByZero",
            "line": line,
            "bug": (
                f"JavaScript division by zero: '{operator}' on line {line} "
                f"silently produces {result_value} instead of throwing."
            ),
            "explanation": (
                "JavaScript does not raise an error when dividing by zero; "
                f"it returns {result_value}. This is almost always a "
                "logic bug."
            ),
            "root_cause": "The divisor is statically known to be zero.",
            "suggested_fix": (
                "Validate the divisor before dividing, or guard the "
                "operation with an explicit check."
            ),
        }

    zero_variables = set(
        re.findall(
            r"\b(?:let|const|var)\s+"
            r"([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*0\b",
            code,
        )
    )

    zero_variables.update(
        re.findall(
            r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*0\b",
            code,
        )
    )

    for variable in zero_variables:
        pattern = re.compile(
            rf"(?P<left>[A-Za-z_$][A-Za-z0-9_$()\[\].]*)"
            rf"\s*(?P<op>/|%)\s*{re.escape(variable)}\b"
        )

        match = pattern.search(code)
        if match:
            operator = match.group("op")
            line = code[:match.start()].count("\n") + 1
            result_value = "Infinity" if operator == "/" else "NaN"

            return {
                "detected": True,
                "error_type": "DivisionByZero",
                "line": line,
                "variable": variable,
                "bug": (
                    f"JavaScript division by zero: variable '{variable}' "
                    f"is assigned zero and used as a divisor on line "
                    f"{line}, silently producing {result_value}."
                ),
                "explanation": (
                    f"The divisor '{variable}' is statically known to "
                    f"contain zero. JavaScript returns {result_value} "
                    "instead of throwing."
                ),
                "root_cause": (
                    f"Variable '{variable}' has value zero before the "
                    "division."
                ),
                "suggested_fix": (
                    f"Validate '{variable}' before using it as a divisor."
                ),
            }

    return None


def _cpp_uninitialized_variable(code):
    declaration_pattern = re.compile(
        r"(?m)^[ \t]*"
        r"(?:const\s+)?"
        r"(?:unsigned\s+|signed\s+)?"
        r"(?:short\s+|long\s+long\s+|long\s+)?"
        r"(?:int|float|double|char|bool)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*;"
    )

    parameter_names = set()
    for params_match in re.finditer(
        r"\(([^)]*)\)\s*(?:const\s*)?\{",
        code,
    ):
        for raw in params_match.group(1).split(","):
            name = (
                raw.strip()
                .split("=")[0]
                .split("[")[0]
                .strip()
                .split()[-1] if raw.strip() else ""
            )
            name = re.sub(r"[^A-Za-z0-9_]", "", name)
            if name:
                parameter_names.add(name)

    for match in declaration_pattern.finditer(code):
        variable = match.group(1)

        if variable in parameter_names:
            continue

        declaration_end = match.end()
        remaining = code[declaration_end:]

        use_match = re.search(
            rf"\b{re.escape(variable)}\b",
            remaining,
        )

        if not use_match:
            continue

        before_use = remaining[:use_match.start()]

        if re.search(
            rf"\b{re.escape(variable)}\s*(?:=[^=]|\+\+|--|\+=|-=|\*=|/=|%=)",
            before_use,
        ):
            continue

        if re.search(
            rf"[:,\s]\s*{re.escape(variable)}\s*\(",
            before_use,
        ):
            continue

        if re.search(
            rf"{re.escape(variable)}\s*\{{",
            before_use,
        ):
            continue

        if re.search(
            rf"\b(?:int|float|double|char|bool|long|short|signed|unsigned)\s+"
            rf"{re.escape(variable)}\s*(?:=|;)",
            before_use,
        ):
            continue

        if re.search(
            rf"&\s*{re.escape(variable)}\b",
            before_use,
        ):
            continue

        line = code[:match.start()].count("\n") + 1

        return {
            "detected": True,
            "error_type": "UninitializedVariable",
            "line": line,
            "variable": variable,
            "bug": (
                f"Uninitialized variable '{variable}' is declared without "
                "an initial value and is later read."
            ),
            "explanation": (
                f"The local variable '{variable}' is declared but not "
                "initialized before it is used."
            ),
            "root_cause": (
                f"Variable '{variable}' has an indeterminate value before "
                "its first use."
            ),
            "suggested_fix": (
                f"Initialize '{variable}' when declaring it, for example "
                f"'{variable} = 0' or use brace initialization."
            ),
        }

    return None


def detect_compiled_language_runtime_error(code, language):
    language = canonical_language(language)

    if language == "java":
        return (
            _java_division_by_zero(code)
            or _c_cpp_division_by_zero_via_call(code, "java")
        )

    if language == "c":
        return (
            _compiled_division_by_zero(code, "c")
            or _c_cpp_division_by_zero_via_call(code, "c")
        )

    if language == "javascript":
        return _javascript_division_by_zero(code)

    if language == "cpp":
        division_error = _compiled_division_by_zero(code, "cpp")
        if division_error:
            return division_error

        call_error = _c_cpp_division_by_zero_via_call(code, "cpp")
        if call_error:
            return call_error

        return _cpp_uninitialized_variable(code)

    return None


# ============================================================
# LOCAL EXECUTION
# ============================================================

def run_local_code_execution(code, language):
    language = canonical_language(language)

    if not ENABLE_CODE_EXECUTION:
        return {
            "supported": True,
            "status": "disabled",
            "error_type": None,
            "stdout": "",
            "stderr": "Local code execution is disabled.",
            "returncode": None,
        }

    code = str(code)

    if len(code) > MAX_AI_CODE_LENGTH:
        return {
            "supported": True,
            "status": "blocked",
            "error_type": "ExecutionSizeLimit",
            "stdout": "",
            "stderr": "Code exceeds the local execution size limit.",
            "returncode": None,
        }

    if language == "html":
        return _validate_html(code)

    if language == "css":
        return _validate_css(code)

    with tempfile.TemporaryDirectory(prefix="bugai_exec_") as temp_dir:

        if language == "python":
            if not _tool_available(os.sys.executable):
                return {
                    "supported": False,
                    "status": "unavailable",
                    "error_type": "PythonUnavailable",
                    "stdout": "",
                    "stderr": "Python executable was not found.",
                    "returncode": None,
                }

            source = os.path.join(temp_dir, "main.py")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(code)
            result = _run_process([os.sys.executable, source], temp_dir)

        elif language == "javascript":
            if not _tool_available("node"):
                return {
                    "supported": False,
                    "status": "unavailable",
                    "error_type": "NodeUnavailable",
                    "stdout": "",
                    "stderr": (
                        "Node.js was not found. Install Node.js and "
                        "restart the backend."
                    ),
                    "returncode": None,
                }

            source = os.path.join(temp_dir, "main.js")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(code)
            result = _run_process(["node", source], temp_dir)

        elif language == "java":
            if (
                not _tool_available("javac")
                or not _tool_available("java")
            ):
                return {
                    "supported": False,
                    "status": "unavailable",
                    "error_type": "JavaUnavailable",
                    "stdout": "",
                    "stderr": (
                        "JDK (javac/java) was not found. Install a JDK "
                        "and restart the backend."
                    ),
                    "returncode": None,
                }

            package_match = re.search(
                r"\bpackage\s+([A-Za-z_][\w.]*)\s*;", code,
            )
            public_class = re.search(
                r"\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)", code,
            )
            class_names = re.findall(
                r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", code,
            )
            main_class = re.search(
                r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)[^{]*\{", code,
            )

            class_name = (
                public_class.group(1) if public_class
                else (main_class.group(1) if main_class
                      else (class_names[0] if class_names else "Main"))
            )
            package_name = (
                package_match.group(1) if package_match else ""
            )

            package_dir = temp_dir
            if package_name:
                package_dir = os.path.join(
                    temp_dir, *package_name.split("."),
                )
                os.makedirs(package_dir, exist_ok=True)

            source = os.path.join(package_dir, class_name + ".java")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(code)

            compile_result = _run_process(
                ["javac", source], temp_dir,
                timeout=max(CODE_EXECUTION_TIMEOUT, 10),
            )

            if (
                compile_result["returncode"] != 0
                or compile_result["timed_out"]
            ):
                result = compile_result
            else:
                fqcn = (
                    f"{package_name}.{class_name}"
                    if package_name else class_name
                )
                result = _run_process(
                    ["java", "-cp", temp_dir, fqcn], temp_dir,
                )

        elif language in {"c", "cpp"}:
            compiler = "g++" if language == "cpp" else "gcc"
            if not _tool_available(compiler):
                return {
                    "supported": False,
                    "status": "unavailable",
                    "error_type": "CompilerUnavailable",
                    "stdout": "",
                    "stderr": (
                        f"{compiler} was not found. Install a C/C++ "
                        "compiler and restart the backend."
                    ),
                    "returncode": None,
                }

            extension = ".cpp" if language == "cpp" else ".c"
            source = os.path.join(temp_dir, "main" + extension)
            executable = os.path.join(
                temp_dir,
                "bugai_program.exe" if os.name == "nt" else "bugai_program",
            )

            with open(source, "w", encoding="utf-8") as handle:
                handle.write(code)

            compile_result = _run_process(
                [compiler, source, "-O0", "-o", executable],
                temp_dir,
                timeout=max(CODE_EXECUTION_TIMEOUT, 10),
            )

            if (
                compile_result["returncode"] != 0
                or compile_result["timed_out"]
            ):
                result = compile_result
            else:
                result = _run_process([executable], temp_dir)

        else:
            return {
                "supported": False,
                "status": "unsupported",
                "error_type": "UnsupportedLanguage",
                "stdout": "",
                "stderr": (
                    f"No local execution adapter is configured for "
                    f"'{language}'."
                ),
                "returncode": None,
            }

        if result.get("timed_out"):
            status = "timeout"
            error_type = "TimeoutError"
        elif result.get("returncode") == 0:
            status = "success"
            error_type = None
        else:
            status = "compile_or_runtime_error"
            error_type = (
                "CompileError"
                if language in {"java", "c", "cpp"}
                else "RuntimeError"
            )

        return {
            "supported": True,
            "status": status,
            "error_type": error_type,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "returncode": result.get("returncode"),
        }


def execution_issue_text(execution_result, language):
    if not execution_result:
        return ""

    if execution_result.get("status") not in {
        "compile_or_runtime_error",
        "validation_error",
        "timeout",
    }:
        return ""

    details = (
        execution_result.get("stderr")
        or execution_result.get("stdout")
        or "Unknown execution error."
    ).strip()

    if len(details) > 1200:
        details = details[:1200] + "..."

    return (
        f"{canonical_language(language).title()} execution check failed: "
        f"{details}"
    )


# ============================================================
# SCOPE-AWARE PYTHON UNDEFINED-NAME ANALYSIS
# ============================================================

def _bound_names(table):
    return {
        symbol.get_name()
        for symbol in table.get_symbols()
        if (
            symbol.is_local()
            or symbol.is_imported()
            or symbol.is_assigned()
            or symbol.is_parameter()
        )
    }


def detect_scope_aware_undefined_names(code):
    undefined = set()

    if _has_wildcard_import(code):
        return undefined

    try:
        table = symtable.symtable(
            code, "submitted_code.py", "exec",
        )
    except (SyntaxError, ValueError):
        return undefined

    module_bound = _bound_names(table)

    def visit(current):
        for symbol in current.get_symbols():
            name = symbol.get_name()

            if (
                not symbol.is_referenced()
                or name in PYTHON_BUILTINS
            ):
                continue

            if (
                symbol.is_imported()
                or symbol.is_local()
                or symbol.is_parameter()
            ):
                continue

            if symbol.is_free():
                continue

            if symbol.is_global():
                if name not in module_bound:
                    undefined.add(name)
                continue

            if (
                current.get_type() == "module"
                and name not in module_bound
            ):
                undefined.add(name)

        for child in current.get_children():
            visit(child)

    visit(table)
    return undefined


def filter_false_positive_undefined_issues(code, static_issues):
    issues = normalize_static_issues(static_issues)
    if not issues:
        return []

    has_wildcard = _has_wildcard_import(code)

    if has_wildcard:
        filtered = []
        for issue in issues:
            lower = issue.lower()
            if (
                "undefined name" in lower
                or "undefined variable" in lower
                or "is not defined" in lower
                or "possible undefined" in lower
            ):
                continue
            filtered.append(issue)
        return list(dict.fromkeys(filtered))

    undefined = detect_scope_aware_undefined_names(code)
    filtered = []

    for issue in issues:
        lower = issue.lower()

        if not (
            "undefined name" in lower
            or "undefined variable" in lower
            or "is not defined" in lower
            or "possible undefined" in lower
        ):
            filtered.append(issue)
            continue

        match = re.search(r"['\"]([^'\"]+)['\"]", issue)
        name = match.group(1) if match else ""

        if name and name in undefined:
            filtered.append(issue)

    return list(dict.fromkeys(filtered))


def build_scope_aware_undefined_issues(code):
    return [
        f"submitted_code.py: undefined name '{name}'"
        for name in sorted(detect_scope_aware_undefined_names(code))
    ]


# ============================================================
# RECURSION
# ============================================================

def _function_calls_self(node):
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == node.name
        for child in ast.walk(node)
    )


def _statement_can_terminate(statement, function_name):
    if isinstance(statement, ast.Return):
        if statement.value is None:
            return True
        return not any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == function_name
            for n in ast.walk(statement.value)
        )

    if isinstance(statement, ast.Raise):
        return True

    if isinstance(statement, ast.If):
        return any(
            _statement_can_terminate(child, function_name)
            for child in (statement.body + statement.orelse)
        )

    if isinstance(statement, (ast.For, ast.While, ast.AsyncFor)):
        return any(
            _statement_can_terminate(child, function_name)
            for child in statement.body
        )

    if isinstance(statement, ast.Try):
        blocks = list(statement.body) + [
            child for handler in statement.handlers for child in handler.body
        ]
        return any(
            _statement_can_terminate(child, function_name)
            for child in blocks
        )

    return False


def _function_has_base_case(function_node):
    return any(
        _statement_can_terminate(statement, function_node.name)
        for statement in function_node.body
    )


def detect_recursion_without_base_case(code):
    result = {"detected": False, "function_name": "", "line": 0}

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                _function_calls_self(node)
                and not _function_has_base_case(node)
            ):
                result.update({
                    "detected": True,
                    "function_name": node.name,
                    "line": getattr(node, "lineno", 1),
                })
                return result

    return result


def _get_parameters(function_node):
    args = function_node.args
    return [
        arg.arg
        for arg in (
            list(args.posonlyargs)
            + list(args.args)
            + list(args.kwonlyargs)
        )
    ]


def fix_recursion_without_base_case(code, detection):
    function_name = detection.get("function_name", "")
    if not function_name:
        return "", ""

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "", ""

    target = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ),
        None,
    )

    if target is None:
        return "", ""

    params = _get_parameters(target)
    arg_name = params[0] if params else "n"

    lines = code.splitlines()
    def_index = next(
        (
            i
            for i, line in enumerate(lines)
            if re.match(
                rf"^\s*(?:async\s+)?def\s+"
                rf"{re.escape(function_name)}\s*\(",
                line,
            )
        ),
        None,
    )

    if def_index is None:
        return "", ""

    indent = (
        len(lines[def_index]) - len(lines[def_index].lstrip())
    )
    body_prefix = " " * (indent + 4)

    call_pattern = re.compile(
        rf"\b{re.escape(function_name)}"
        rf"\(\s*{re.escape(arg_name)}\s*\)"
    )

    rewritten_body = [
        call_pattern.sub(f"{function_name}({arg_name} - 1)", line)
        for line in lines[def_index + 1:]
    ]

    corrected = "\n".join(
        lines[:def_index + 1]
        + [
            f"{body_prefix}if {arg_name} <= 1:",
            f"{body_prefix}    return 1",
        ]
        + rewritten_body
    )

    try:
        ast.parse(corrected)
    except SyntaxError:
        return "", ""

    return (
        corrected,
        (
            f"Added base-case guard and decremented recursive call "
            f"in '{function_name}' to prevent infinite recursion."
        ),
    )


# ============================================================
# PYFLAKES
# ============================================================

def run_pyflakes(code):
    issues = []
    temp_path = None
    has_wildcard = _has_wildcard_import(code)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8",
        ) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        result = subprocess.run(
            [os.sys.executable, "-m", "pyflakes", temp_path],
            capture_output=True, text=True, timeout=8,
        )

        output = (result.stdout or result.stderr or "").strip()

        for raw in output.splitlines():
            line = raw.strip()
            if not line:
                continue

            line = line.replace(temp_path, "submitted_code.py")
            lower = line.lower()

            if (
                "may be undefined" in lower
                and "star imports" in lower
            ):
                continue

            if "used; unable to detect undefined names" in lower:
                continue

            if has_wildcard and (
                "undefined name" in lower
                or "undefined variable" in lower
                or "is not defined" in lower
            ):
                continue

            issues.append(line)

    except subprocess.TimeoutExpired:
        issues.append("Pyflakes analysis timed out.")

    except Exception as error:
        print("Pyflakes error:", error)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return list(dict.fromkeys(issues))


# ============================================================
# PYTHON RUNTIME DETECTION
# ============================================================

def _literal(node):
    try:
        return ast.literal_eval(node), True
    except (ValueError, TypeError, SyntaxError, MemoryError):
        return None, False


def _module_constants(tree):
    values = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value, ok = _literal(node.value)
            if ok:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        values[target.id] = value

        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, ok = _literal(node.value)
            if ok and isinstance(node.target, ast.Name):
                values[node.target.id] = value

    return values


def _zero_division(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            continue

        value, ok = _literal(node.right)
        if ok and value == 0:
            op = {ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}.get(
                type(node.op), "/",
            )
            return {
                "detected": True,
                "error_type": "ZeroDivisionError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    "ZeroDivisionError: division by zero detected "
                    f"on line {getattr(node, 'lineno', 1)}."
                ),
                "explanation": (
                    f"The '{op}' operator uses zero as the divisor. "
                    "Python will raise ZeroDivisionError at runtime."
                ),
                "root_cause": (
                    "A calculation divides or takes a remainder by zero."
                ),
                "suggested_fix": (
                    "Check that the divisor is not zero before "
                    "performing the calculation."
                ),
            }

    constants = _module_constants(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            continue
        if (
            isinstance(node.right, ast.Name)
            and constants.get(node.right.id) == 0
        ):
            return {
                "detected": True,
                "error_type": "ZeroDivisionError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"ZeroDivisionError: variable "
                    f"'{node.right.id}' has value zero "
                    "and is used as a divisor."
                ),
                "explanation": (
                    f"The divisor variable '{node.right.id}' "
                    "is statically known to contain zero."
                ),
                "root_cause": (
                    f"Variable '{node.right.id}' has value zero."
                ),
                "suggested_fix": (
                    f"Validate '{node.right.id}' before division "
                    "and handle the zero case explicitly."
                ),
            }

    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        if not isinstance(call.func, ast.Name):
            continue

        function = functions.get(call.func.id)
        if function is None:
            continue

        params = _get_parameters(function)
        passed = {}

        for i, arg in enumerate(call.args):
            if i >= len(params):
                break
            value, ok = _literal(arg)
            if (
                not ok
                and isinstance(arg, ast.Name)
                and arg.id in constants
            ):
                value = constants[arg.id]
                ok = True
            if ok:
                passed[params[i]] = value

        for node in ast.walk(function):
            if not isinstance(node, ast.BinOp):
                continue
            if not isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                continue
            if (
                isinstance(node.right, ast.Name)
                and passed.get(node.right.id) == 0
            ):
                return {
                    "detected": True,
                    "error_type": "ZeroDivisionError",
                    "line": getattr(node, "lineno", 1),
                    "bug": (
                        f"ZeroDivisionError: parameter "
                        f"'{node.right.id}' receives zero "
                        "and is used as a divisor."
                    ),
                    "explanation": (
                        f"The call to '{function.name}()' "
                        f"passes zero to '{node.right.id}', "
                        "which is used in division."
                    ),
                    "root_cause": (
                        f"Parameter '{node.right.id}' has "
                        "runtime value zero."
                    ),
                    "suggested_fix": (
                        f"Validate '{node.right.id}' before "
                        "division and handle the zero case explicitly."
                    ),
                }

    return None


def _index_error(tree):
    bindings = _module_constants(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue

        index, ok = _literal(node.slice)
        if not ok or not isinstance(index, int):
            continue

        sequence = None
        if isinstance(node.value, ast.Name):
            sequence = bindings.get(node.value.id)
        else:
            sequence, _ = _literal(node.value)

        if isinstance(sequence, (list, tuple, str)):
            if index >= len(sequence) or index < -len(sequence):
                return {
                    "detected": True,
                    "error_type": "IndexError",
                    "line": getattr(node, "lineno", 1),
                    "bug": f"IndexError: index {index} is out of range.",
                    "explanation": (
                        f"The sequence has {len(sequence)} "
                        f"item(s), but index {index} is invalid."
                    ),
                    "root_cause": (
                        "The code accesses a sequence index "
                        "that does not exist."
                    ),
                    "suggested_fix": (
                        "Use a valid index or check the "
                        "sequence length first."
                    ),
                }

    return None


def _key_error(tree):
    bindings = _module_constants(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name):
            continue

        mapping = bindings.get(node.value.id)
        if not isinstance(mapping, dict):
            continue

        key, ok = _literal(node.slice)
        if ok and key not in mapping:
            return {
                "detected": True,
                "error_type": "KeyError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"KeyError: key {key!r} "
                    f"does not exist in dictionary "
                    f"'{node.value.id}'."
                ),
                "explanation": (
                    f"The code accesses key {key!r}, "
                    f"but that key is not present."
                ),
                "root_cause": (
                    "The requested dictionary key is missing."
                ),
                "suggested_fix": (
                    "Use dict.get() or check the key before using []."
                ),
            }

    return None


def _type_error(tree):
    bindings = _module_constants(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, ast.Add):
            continue

        left, left_ok = _literal(node.left)
        right, right_ok = _literal(node.right)

        if isinstance(node.left, ast.Name) and node.left.id in bindings:
            left = bindings[node.left.id]
            left_ok = True
        if isinstance(node.right, ast.Name) and node.right.id in bindings:
            right = bindings[node.right.id]
            right_ok = True

        if not (left_ok and right_ok):
            continue

        incompatible = (
            isinstance(left, str)
            and isinstance(right, (int, float))
        ) or (
            isinstance(right, str)
            and isinstance(left, (int, float))
        )

        if incompatible:
            return {
                "detected": True,
                "error_type": "TypeError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    "TypeError: incompatible string and numeric "
                    "values are combined."
                ),
                "explanation": (
                    "Python does not allow a string and a number "
                    "to be added directly with '+'."
                ),
                "root_cause": "Operands have incompatible types.",
                "suggested_fix": (
                    "Convert the numeric value to str() or use an f-string."
                ),
            }

    return None


def _attribute_error(tree):
    class_attrs = {}

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        attrs = set()

        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                attrs.add(child.name)

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        attrs.add(target.attr)

            elif isinstance(child, ast.AnnAssign):
                target = child.target
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attrs.add(target.attr)

            elif isinstance(child, ast.AugAssign):
                target = child.target
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attrs.add(target.attr)

        class_attrs[node.name] = attrs

    instance_classes = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        value = node.value
        if not isinstance(value, ast.Call):
            continue
        if not isinstance(value.func, ast.Name):
            continue
        if value.func.id not in class_attrs:
            continue

        for target in node.targets:
            if isinstance(target, ast.Name):
                instance_classes[target.id] = value.func.id

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not isinstance(node.value, ast.Name):
            continue

        variable = node.value.id
        if variable not in instance_classes:
            continue

        class_name = instance_classes[variable]
        if node.attr not in class_attrs[class_name]:
            return {
                "detected": True,
                "error_type": "AttributeError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"AttributeError: object '{variable}' "
                    f"does not define attribute '{node.attr}'."
                ),
                "explanation": (
                    f"The '{class_name}' object does not define "
                    f"attribute '{node.attr}'."
                ),
                "root_cause": (
                    f"Attribute '{node.attr}' is not created by the class."
                ),
                "suggested_fix": (
                    f"Use an existing '{class_name}' attribute or "
                    f"define '{node.attr}' before accessing it."
                ),
            }

    return None


def _value_error(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in {"int", "float"}:
            continue
        if not node.args:
            continue

        value, ok = _literal(node.args[0])
        if not ok or not isinstance(value, str):
            continue

        try:
            (int(value) if node.func.id == "int" else float(value))
        except ValueError:
            return {
                "detected": True,
                "error_type": "ValueError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"ValueError: {node.func.id}() cannot convert "
                    f"{value!r} to a number."
                ),
                "explanation": (
                    f"The literal {value!r} is not valid input."
                ),
                "root_cause": (
                    "The string cannot be parsed as the requested number."
                ),
                "suggested_fix": (
                    "Validate the input and handle ValueError."
                ),
            }

    return None


def _tuple_mutation(tree):
    tuple_names = set()

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value, ok = _literal(node.value)
            if ok and isinstance(value, tuple):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        tuple_names.add(target.id)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not node.targets:
            continue

        target = node.targets[0]

        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id in tuple_names
        ):
            return {
                "detected": True,
                "error_type": "TypeError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"TypeError: tuple '{target.value.id}' "
                    "does not support item assignment."
                ),
                "explanation": (
                    "The code tries to modify an immutable tuple."
                ),
                "root_cause": (
                    "A tuple item is assigned after tuple creation."
                ),
                "suggested_fix": (
                    "Use a list when the data needs to be modified."
                ),
            }

    return None


def _set_remove(tree):
    sets = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value, ok = _literal(node.value)
            if ok and isinstance(value, set):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        sets[target.id] = value

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "remove"
            and isinstance(node.func.value, ast.Name)
            and node.args
        ):
            continue

        values = sets.get(node.func.value.id)
        item, ok = _literal(node.args[0])

        if values is not None and ok and item not in values:
            return {
                "detected": True,
                "error_type": "KeyError",
                "line": getattr(node, "lineno", 1),
                "bug": (
                    f"KeyError: set '{node.func.value.id}' "
                    f"does not contain item {item!r}."
                ),
                "explanation": (
                    "set.remove() raises KeyError when the item "
                    "does not exist."
                ),
                "root_cause": (
                    "remove() requires the requested item to exist."
                ),
                "suggested_fix": (
                    "Use discard() or check membership first."
                ),
            }

    return None


def detect_local_runtime_error(code, language):
    language = canonical_language(language)

    if language != "python":
        return detect_compiled_language_runtime_error(code, language)

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for detector in (
        _zero_division,
        _index_error,
        _key_error,
        _type_error,
        _attribute_error,
        _value_error,
        _tuple_mutation,
        _set_remove,
    ):
        issue = detector(tree)
        if issue:
            return issue

    return None


# ============================================================
# SAFE RUNTIME FIXES
# ============================================================

def _replace_source_segment(code, node, replacement):
    segment = ast.get_source_segment(code, node)
    if not segment:
        return code, False

    start_line = getattr(node, "lineno", 0)
    end_line = getattr(node, "end_lineno", start_line)
    if start_line != end_line:
        return code, False

    lines = code.splitlines(keepends=True)
    if not (1 <= start_line <= len(lines)):
        return code, False

    line = lines[start_line - 1]
    position = line.find(segment)
    if position < 0:
        return code, False

    lines[start_line - 1] = (
        line[:position] + replacement + line[position + len(segment):]
    )

    new_code = "".join(lines)

    try:
        compile(new_code, "<submitted_code>", "exec")
    except SyntaxError:
        return code, False

    return new_code, True


def _insert_zero_guard(code, function_node, parameter_name):
    lines = code.splitlines(keepends=True)
    if not function_node.body:
        return code, False

    first_body = function_node.body[0]
    insert_after = getattr(first_body, "lineno", function_node.lineno)

    if (
        isinstance(first_body, ast.Expr)
        and isinstance(first_body.value, ast.Constant)
        and isinstance(first_body.value.value, str)
    ):
        insert_after = getattr(first_body, "end_lineno", first_body.lineno)

    body_line_no = getattr(first_body, "lineno", function_node.lineno + 1)

    if 1 <= body_line_no <= len(lines):
        body_line = lines[body_line_no - 1]
        indent = body_line[:len(body_line) - len(body_line.lstrip())]
    else:
        def_line = lines[function_node.lineno - 1]
        parent_indent = def_line[:len(def_line) - len(def_line.lstrip())]
        indent = parent_indent + "    "

    guard = (
        f"{indent}if {parameter_name} == 0:\n"
        f"{indent}    return None\n"
    )

    insert_index = insert_after - 1
    lines.insert(insert_index, guard)

    new_code = "".join(lines)

    try:
        compile(new_code, "<submitted_code>", "exec")
    except SyntaxError:
        return code, False

    return new_code, True


def _fix_compiled_division_by_zero(code, runtime_error, language):
    if not runtime_error:
        return code, ""
    if runtime_error.get("error_type") != "DivisionByZero":
        return code, ""

    language = canonical_language(language)
    variable = runtime_error.get("variable", "")
    neq = "!==" if language == "javascript" else "!="

    if variable:
        pattern = re.compile(
            rf"(?P<left>[A-Za-z_$][A-Za-z0-9_$()\[\].]*)"
            rf"\s*(?P<op>/|%)\s*{re.escape(variable)}\b"
        )

        match = pattern.search(code)

        if match:
            left = match.group("left")
            operator = match.group("op")
            else_value = "0"

            if language == "java":
                if re.search(rf"\blong\s+{re.escape(left)}\b", code):
                    else_value = "0L"
                elif re.search(
                    rf"\b(?:short|byte)\s+{re.escape(left)}\b", code,
                ):
                    else_value = "(short) 0"

            replacement = (
                f"({variable} {neq} 0 ? "
                f"{left} {operator} {variable} : {else_value})"
            )

            fixed = (
                code[:match.start()] + replacement + code[match.end():]
            )
            return (
                fixed,
                f"Added a zero-divisor guard for '{variable}'.",
            )

    pattern = re.compile(
        r"(?P<left>[A-Za-z0-9_$][A-Za-z0-9_$()\[\].]*)"
        r"\s*(?P<op>/|%)\s*0(?![0-9.])"
    )

    match = pattern.search(code)

    if match:
        fixed = code[:match.start()] + "0" + code[match.end():]
        return (
            fixed,
            "Replaced a literal division-by-zero expression with 0.",
        )

    return code, ""


def _fix_cpp_uninitialized_variable(code, runtime_error):
    if not runtime_error:
        return code, ""
    if runtime_error.get("error_type") != "UninitializedVariable":
        return code, ""

    variable = runtime_error.get("variable", "")
    if not variable:
        return code, ""

    pattern = re.compile(
        rf"(?m)^([ \t]*)"
        rf"((?:const\s+)?"
        rf"(?:unsigned\s+|signed\s+)?"
        rf"(?:short\s+|long\s+long\s+|long\s+)?"
        rf"(?:int|float|double|char|bool))"
        rf"(\s+{re.escape(variable)})\s*;"
    )

    match = pattern.search(code)
    if not match:
        return code, ""

    fixed = (
        code[:match.start()]
        + match.group(1)
        + match.group(2)
        + match.group(3)
        + " = 0;"
        + code[match.end():]
    )

    return (
        fixed,
        f"Initialized uninitialized variable '{variable}' to 0.",
    )


# ============================================================
# JAVASCRIPT HELPERS
# ============================================================

JS_GLOBAL_NAMES = {
    "console", "window", "document", "global", "globalThis", "process",
    "require", "module", "exports", "JSON", "Math", "Object", "Array",
    "String", "Number", "Boolean", "Date", "RegExp", "Promise", "Map",
    "Set", "WeakMap", "WeakSet", "Symbol", "Error", "TypeError",
    "RangeError", "SyntaxError", "ReferenceError", "EvalError", "URIError",
    "Infinity", "NaN", "undefined", "null", "true", "false", "this",
    "arguments", "eval", "parseInt", "parseFloat", "isNaN", "isFinite",
    "encodeURI", "decodeURI", "encodeURIComponent", "decodeURIComponent",
    "setTimeout", "setInterval", "clearTimeout", "clearInterval", "fetch",
    "alert", "confirm", "prompt", "localStorage", "sessionStorage",
    "location", "navigator", "history", "performance", "Buffer", "URL",
    "URLSearchParams",
}


def _parse_param_list(text):
    params = []
    for raw in text.split(","):
        name = raw.strip().split("=")[0].strip()
        name = name.lstrip(".")
        if not re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", name):
            continue
        if name:
            params.append(name)
    return params


def _javascript_defined_names(code):
    names = set()

    for match in re.finditer(
        r"\b(?:let|const|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)", code,
    ):
        names.add(match.group(1))

    for match in re.finditer(
        r"\b(?:let|const|var)\s+([^;=\n]+)", code,
    ):
        for part in match.group(1).split(","):
            candidate = part.strip().split("=")[0].strip()
            if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", candidate):
                names.add(candidate)

    for match in re.finditer(
        r"\b(?:let|const|var)\s*\{([^}]+)\}", code,
    ):
        for part in match.group(1).split(","):
            candidate = (
                part.strip().split(":")[-1].split("=")[0].strip()
            )
            if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", candidate):
                names.add(candidate)

    for match in re.finditer(
        r"\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(([^)]*)\)", code,
    ):
        names.add(match.group(1))
        for param in _parse_param_list(match.group(2)):
            names.add(param)

    for match in re.finditer(
        r"(?<![\w$])function\s*\(([^)]*)\)", code,
    ):
        for param in _parse_param_list(match.group(1)):
            names.add(param)

    for match in re.finditer(r"\(([^)]*)\)\s*=>", code):
        for param in _parse_param_list(match.group(1)):
            names.add(param)

    for match in re.finditer(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*=>", code):
        names.add(match.group(1))

    for match in re.finditer(
        r"\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)", code,
    ):
        names.add(match.group(1))

    for match in re.finditer(
        r"\bimport\s+([^;]+?)\s+from\s+", code,
    ):
        text = match.group(1).strip()
        if text.startswith("{"):
            text = text.strip("{}")
            for part in text.split(","):
                candidate = part.strip().split(" as ")[-1].strip()
                if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", candidate):
                    names.add(candidate)
        else:
            candidate = text.split(",")[0].strip()
            if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", candidate):
                names.add(candidate)

    return names


def _js_undefined_names_from_stderr(stderr):
    names = []
    patterns = [
        r"ReferenceError:\s*"
        r"([A-Za-z_$][A-Za-z0-9_$]*)\s+is\s+not\s+defined",
        r"ReferenceError:\s*Cannot\s+access\s+"
        r"'([A-Za-z_$][A-Za-z0-9_$]*)'\s+before\s+initialization",
    ]
    for pat in patterns:
        for match in re.finditer(pat, stderr):
            name = match.group(1)
            if name not in names:
                names.append(name)
    return names


def _js_find_parameter_names(code, fn_name):
    match = re.search(
        rf"\bfunction\s+{re.escape(fn_name)}\s*\(([^)]*)\)", code,
    )
    if match:
        return _parse_param_list(match.group(1))

    match = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(fn_name)}\s*=\s*"
        rf"\(([^)]*)\)\s*=>",
        code,
    )
    if match:
        return _parse_param_list(match.group(1))

    match = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(fn_name)}\s*=\s*"
        rf"([A-Za-z_$][A-Za-z0-9_$]*)\s*=>",
        code,
    )
    if match:
        return [match.group(1)]

    return None


def _js_is_declared_variable(code, name):
    return bool(
        re.search(
            rf"\b(?:let|const|var)\s+{re.escape(name)}\b", code,
        )
    )


def _try_fix_javascript_name(code, undefined_name, defined_names):
    if undefined_name in JS_GLOBAL_NAMES:
        return code, ""

    aliases = SEMANTIC_VARIABLE_ALIASES.get(
        undefined_name.lower(), [],
    )

    for candidate in aliases:
        if candidate in defined_names:
            fixed = re.sub(
                rf"\b{re.escape(undefined_name)}\b", candidate, code,
            )
            return (
                fixed,
                f"Replaced undefined JavaScript variable "
                f"'{undefined_name}' with '{candidate}' "
                "(semantic alias).",
            )

    for call_match in re.finditer(
        r"\b([A-Za-z_$][A-Za-z0-9_$.]*)\s*\(([^()]*)\)", code,
    ):
        fn_name = call_match.group(1).split(".")[-1]
        args_text = call_match.group(2)
        args = [a.strip() for a in args_text.split(",")]

        position = None
        for i, arg in enumerate(args):
            if re.search(rf"\b{re.escape(undefined_name)}\b", arg):
                position = i
                break

        if position is None:
            continue

        params = _js_find_parameter_names(code, fn_name)
        if not params or position >= len(params):
            continue

        param = params[position]
        if (
            param
            and param != undefined_name
            and _js_is_declared_variable(code, param)
        ):
            fixed = re.sub(
                rf"\b{re.escape(undefined_name)}\b", param, code,
            )
            return (
                fixed,
                f"Replaced undefined JavaScript variable "
                f"'{undefined_name}' with '{param}' "
                f"(parameter {position + 1} of '{fn_name}').",
            )

    typo_correction = JS_COMMON_TYPO_FIXES.get(undefined_name.lower())
    if typo_correction and typo_correction != undefined_name:
        fixed = re.sub(
            rf"\b{re.escape(undefined_name)}\b",
            typo_correction,
            code,
        )
        if fixed != code:
            return (
                fixed,
                f"Fixed common JavaScript typo: "
                f"'{undefined_name}' → '{typo_correction}'.",
            )

    best = None
    for defined in defined_names:
        if len(defined) < 4 or defined == undefined_name:
            continue
        ratio = difflib.SequenceMatcher(
            None, undefined_name.lower(), defined.lower(),
        ).ratio()
        if ratio >= 0.80 and (best is None or ratio > best[2]):
            best = (undefined_name, defined, ratio)

    if best:
        wrong, right, _ = best
        fixed = re.sub(rf"\b{re.escape(wrong)}\b", right, code)
        return (
            fixed,
            f"Replaced '{wrong}' with '{right}' (likely typo).",
        )

    return code, ""


def _fix_javascript_reference_error(code, execution_result):
    if not execution_result:
        return code, ""

    stderr = str(execution_result.get("stderr", "") or "")
    if not stderr:
        return code, ""

    undefined_names = _js_undefined_names_from_stderr(stderr)
    if not undefined_names:
        return code, ""

    defined_names = _javascript_defined_names(code)
    corrected = code
    messages = []

    for undefined_name in undefined_names:
        fixed, msg = _try_fix_javascript_name(
            corrected, undefined_name, defined_names,
        )
        if msg:
            corrected = fixed
            messages.append(msg)
            defined_names = _javascript_defined_names(corrected)

    if not messages:
        return code, ""

    return corrected, " ".join(messages)


def apply_safe_runtime_fix(code, runtime_error, language="python"):
    if not runtime_error:
        return code, ""

    language = canonical_language(language)
    error_type = runtime_error.get("error_type", "")

    if language == "html":
        if error_type == "HTMLValidationError":
            fixed, message = fix_html_structure(code)
            if fixed != code:
                return fixed, message
        return (
            code,
            runtime_error.get(
                "suggested_fix", "Review the HTML structure.",
            ),
        )

    if language == "css":
        if error_type == "CSSValidationError":
            fixed, message = fix_css_structure(code)
            if fixed != code:
                recheck = _validate_css(fixed)
                if recheck.get("status") == "success":
                    return fixed, message
                return (
                    code,
                    "CSS auto-fix was attempted but the corrected "
                    "styles could not be validated. Manual review "
                    "required. Details: "
                    + recheck.get("stderr", "unknown"),
                )
        return (
            code,
            runtime_error.get(
                "suggested_fix", "Review the CSS braces and syntax.",
            ),
        )

    if language in {"java", "c", "cpp", "javascript"}:
        if error_type == "DivisionByZero":
            return _fix_compiled_division_by_zero(
                code, runtime_error, language,
            )

        if language == "cpp" and error_type == "UninitializedVariable":
            return _fix_cpp_uninitialized_variable(code, runtime_error)

        return (
            code,
            runtime_error.get(
                "suggested_fix", "Review the reported runtime issue.",
            ),
        )

    original = str(code)

    try:
        tree = ast.parse(original)
    except SyntaxError:
        return (original, runtime_error.get("suggested_fix", ""))

    if error_type == "ZeroDivisionError":
        bug = runtime_error.get("bug", "")
        param_match = re.search(
            r"parameter ['\"]([^'\"]+)['\"]", bug,
        )

        if param_match:
            parameter_name = param_match.group(1)
            explanation = runtime_error.get("explanation", "")
            fn_match = re.search(
                r"call to ['\"]([A-Za-z_][A-Za-z0-9_]*)\(\)['\"]",
                explanation,
            )
            function_name = fn_match.group(1) if fn_match else ""

            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                if function_name and node.name != function_name:
                    continue

                uses_parameter = any(
                    isinstance(child, ast.BinOp)
                    and isinstance(
                        child.op, (ast.Div, ast.FloorDiv, ast.Mod),
                    )
                    and isinstance(child.right, ast.Name)
                    and child.right.id == parameter_name
                    for child in ast.walk(node)
                )

                if uses_parameter:
                    fixed, changed = _insert_zero_guard(
                        original, node, parameter_name,
                    )
                    if changed:
                        return (
                            fixed,
                            (
                                f"Added a zero-divisor guard "
                                f"for '{parameter_name}' "
                                f"in '{node.name}()'."
                            ),
                        )

        constants = _module_constants(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp):
                continue
            if not isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                continue

            zero_divisor = (
                isinstance(node.right, ast.Constant)
                and node.right.value == 0
            ) or (
                isinstance(node.right, ast.Name)
                and constants.get(node.right.id) == 0
            )

            if not zero_divisor:
                continue

            fixed, changed = _replace_source_segment(
                original, node, "None",
            )
            if changed:
                return (
                    fixed,
                    "Replaced the statically proven "
                    "division-by-zero expression with "
                    "None to prevent ZeroDivisionError.",
                )

    if error_type == "IndexError":
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue

            index, valid = _literal(node.slice)
            if not valid or not isinstance(index, int):
                continue

            sequence_text = ast.get_source_segment(original, node.value)
            access_text = ast.get_source_segment(original, node)
            if not sequence_text or not access_text:
                continue

            replacement = (
                f"({access_text} if "
                f"0 <= {index} < len({sequence_text}) "
                "else None)"
            )

            fixed, changed = _replace_source_segment(
                original, node, replacement,
            )
            if changed:
                return (
                    fixed,
                    f"Added a bounds check for index "
                    f"{index} to prevent IndexError.",
                )

    if error_type == "KeyError":
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            if not isinstance(node.value, ast.Name):
                continue

            mapping = _module_constants(tree).get(node.value.id)
            key, valid = _literal(node.slice)

            if (
                not isinstance(mapping, dict)
                or not valid
                or key in mapping
            ):
                continue

            key_text = ast.get_source_segment(original, node.slice)
            if not key_text:
                continue

            fixed, changed = _replace_source_segment(
                original, node, f"{node.value.id}.get({key_text})",
            )
            if changed:
                return (
                    fixed,
                    f"Changed '{node.value.id}[key]' "
                    "to .get(key) to prevent KeyError.",
                )

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "remove"
                and isinstance(node.func.value, ast.Name)
            ):
                fixed = original.replace(
                    f"{node.func.value.id}.remove(",
                    f"{node.func.value.id}.discard(",
                    1,
                )
                if fixed != original:
                    return (
                        fixed,
                        f"Changed '{node.func.value.id}.remove()' "
                        "to discard() so a missing item "
                        "does not raise KeyError.",
                    )

    if error_type == "TypeError":
        bug = runtime_error.get("bug", "").lower()

        if "incompatible string" in bug or "string and numeric" in bug:
            for node in ast.walk(tree):
                if not isinstance(node, ast.BinOp):
                    continue
                if not isinstance(node.op, ast.Add):
                    continue

                left_text = ast.get_source_segment(original, node.left)
                right_text = ast.get_source_segment(original, node.right)
                if not left_text or not right_text:
                    continue

                fixed, changed = _replace_source_segment(
                    original,
                    node,
                    f"str({left_text}) + str({right_text})",
                )
                if changed:
                    return (
                        fixed,
                        "Converted the operands to strings "
                        "before concatenation to prevent TypeError.",
                    )

        if "tuple" in bug and "item assignment" in bug:
            for target_node in ast.walk(tree):
                if not isinstance(target_node, ast.Assign):
                    continue
                if not target_node.targets:
                    continue

                target = target_node.targets[0]
                if not isinstance(target, ast.Subscript):
                    continue
                if not isinstance(target.value, ast.Name):
                    continue

                tuple_name = target.value.id

                for declaration in tree.body:
                    if not isinstance(declaration, ast.Assign):
                        continue
                    if not any(
                        isinstance(t, ast.Name) and t.id == tuple_name
                        for t in declaration.targets
                    ):
                        continue

                    literal, valid = _literal(declaration.value)
                    if not valid or not isinstance(literal, tuple):
                        continue

                    source = ast.get_source_segment(
                        original, declaration.value,
                    )
                    if not source:
                        continue
                    if not (
                        source.startswith("(") and source.endswith(")")
                    ):
                        continue

                    fixed, changed = _replace_source_segment(
                        original,
                        declaration.value,
                        "[" + source[1:-1] + "]",
                    )
                    if changed:
                        return (
                            fixed,
                            f"Converted '{tuple_name}' "
                            "from a tuple to a list because "
                            "its items are modified later.",
                        )

    if error_type == "AttributeError":
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if not isinstance(node.value, ast.Name):
                continue

            if isinstance(node.ctx, ast.Store):
                continue

            source = ast.get_source_segment(original, node)
            if not source:
                continue

            replacement = (
                f"getattr({node.value.id}, {node.attr!r}, None)"
            )

            fixed, changed = _replace_source_segment(
                original, node, replacement,
            )
            if changed:
                return (
                    fixed,
                    f"Changed missing attribute access "
                    f"'{source}' to getattr(..., None).",
                )

    if error_type == "ValueError":
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in {"int", "float"}:
                continue
            if not node.args:
                continue

            value, valid = _literal(node.args[0])
            if not valid or not isinstance(value, str):
                continue

            fixed, changed = _replace_source_segment(
                original, node, "None",
            )
            if changed:
                return (
                    fixed,
                    f"Replaced the invalid "
                    f"{node.func.id}({value!r}) conversion "
                    "with None.",
                )

    return (
        original,
        runtime_error.get(
            "suggested_fix",
            "Review the runtime error and apply the suggested validation.",
        ),
    )


# ============================================================
# PYTHON UNDEFINED / TYPO FIXES
# ============================================================

def _python_names(code):
    names = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return names

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.update(_get_parameters(node))
                if node.args.vararg:
                    names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    names.add(node.args.kwarg.arg)
    return names


def auto_fix_undefined_variable(code, undefined_variable):
    if not code or not undefined_variable:
        return code, ""

    original = str(code)
    defined_names = _python_names(original)
    aliases = SEMANTIC_VARIABLE_ALIASES.get(
        undefined_variable.lower(), [],
    )

    for candidate in aliases:
        if candidate in defined_names:
            fixed = re.sub(
                rf"\b{re.escape(undefined_variable)}\b",
                candidate,
                original,
            )
            return (
                fixed,
                f"Changed undefined variable '{undefined_variable}' "
                f"to '{candidate}' (semantic alias).",
            )

    call_pattern = re.compile(
        r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(([^()\n]*)\)"
    )

    for match in call_pattern.finditer(original):
        function_name = match.group(1).split(".")[-1]
        arguments = [x.strip() for x in match.group(2).split(",")]

        position = next(
            (
                i
                for i, arg in enumerate(arguments)
                if re.search(
                    rf"\b{re.escape(undefined_variable)}\b", arg,
                )
            ),
            None,
        )

        if position is None:
            continue

        definition = re.search(
            rf"\bdef\s+{re.escape(function_name)}\s*\(([^)]*)\)\s*:",
            original,
        )
        if not definition:
            continue

        parameters = []
        for parameter in definition.group(1).split(","):
            name = (
                parameter.strip().split("=")[0].split(":")[0].strip()
            )
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                parameters.append(name)

        if position < len(parameters):
            parameter = parameters[position]
            if (
                parameter != undefined_variable
                and parameter in defined_names
            ):
                fixed = re.sub(
                    rf"\b{re.escape(undefined_variable)}\b",
                    parameter,
                    original,
                )
                return (
                    fixed,
                    f"Changed undefined variable "
                    f"'{undefined_variable}' to '{parameter}' "
                    "(matched function parameter).",
                )

    return original, ""


def fix_common_python_typo(code, static_issues=None):
    undefined = extract_undefined_variable(static_issues or [])
    if not undefined:
        return code, ""

    defined_names = list(_python_names(code))
    best = None

    for defined in defined_names:
        if len(defined) < 4 or defined.lower() in PYTHON_BUILTINS:
            continue
        ratio = difflib.SequenceMatcher(
            None, undefined.lower(), defined.lower(),
        ).ratio()
        if ratio >= 0.80 and (best is None or ratio > best[2]):
            best = (undefined, defined, ratio)

    if not best:
        return code, ""

    wrong, right, _ = best
    fixed = re.sub(rf"\b{re.escape(wrong)}\b", right, code)
    if fixed == code:
        return code, ""
    return (fixed, f"Changed '{wrong}' to '{right}' (likely typo).")


def fix_python_missing_colons(code):
    lines = code.splitlines()
    changed = []

    patterns = (
        r"^(if|elif|else|for|while|try|except|finally|with|class)\b.+$",
        r"^(def|async\s+def)\s+"
        r"[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*$",
    )

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.endswith(":"):
            continue
        if any(re.match(pattern, stripped) for pattern in patterns):
            lines[i] = line + ":"
            changed.append(f"Added missing ':' on line {i + 1}.")

    return ("\n".join(lines), " ".join(changed))


def apply_automatic_fixes(
    code, language, static_issues=None, execution_result=None,
):
    language = canonical_language(language)

    if language == "html":
        fixed, message = fix_html_structure(code)
        return (fixed, [message] if message else [])

    if language == "css":
        fixed, message = fix_css_structure(code)
        return (fixed, [message] if message else [])

    if language == "javascript" and execution_result:
        fixed, message = _fix_javascript_reference_error(
            code, execution_result,
        )
        if message:
            return fixed, [message]
        return code, []

    if language != "python":
        return code, []

    corrected = code
    messages = []

    undefined = extract_undefined_variable(static_issues or [])

    if undefined:
        corrected, message = auto_fix_undefined_variable(
            corrected, undefined,
        )
        if message:
            messages.append(message)

    typo_fixed, typo_message = fix_common_python_typo(
        corrected, static_issues,
    )
    if typo_message:
        corrected = typo_fixed
        messages.append(typo_message)

    colon_fixed, colon_message = fix_python_missing_colons(corrected)
    if colon_message and colon_fixed != corrected:
        corrected = colon_fixed
        messages.append(colon_message)

    if corrected != code and not is_valid_python_code(corrected):
        return code, []

    return corrected, messages


# ============================================================
# METRICS / SECURITY / ADVANCED ANALYSIS
# ============================================================

def calculate_complexity(code, language):
    lines = len(code.splitlines())

    if language.lower() != "python":
        return {
            "total_lines": lines,
            "functions": len(re.findall(r"\bfunction\b|\bdef\b", code)),
            "classes": len(re.findall(r"\bclass\b", code)),
            "decision_points": len(
                re.findall(r"\b(if|elif|for|while|case|catch)\b|&&|\|\|", code)
            ),
        }

    try:
        tree = ast.parse(code)
        return {
            "total_lines": lines,
            "functions": sum(
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                for n in ast.walk(tree)
            ),
            "classes": sum(
                isinstance(n, ast.ClassDef) for n in ast.walk(tree)
            ),
            "decision_points": sum(
                isinstance(
                    n,
                    (ast.If, ast.For, ast.While, ast.Try, ast.IfExp, ast.BoolOp),
                )
                for n in ast.walk(tree)
            ),
        }
    except SyntaxError:
        return {
            "total_lines": lines,
            "functions": len(re.findall(r"\bdef\b", code)),
            "classes": len(re.findall(r"\bclass\b", code)),
            "decision_points": len(
                re.findall(r"\b(if|elif|for|while|try|and|or)\b", code)
            ),
        }


def calculate_quality_score(code, static_issues):
    score = 100 - min(40, len(static_issues) * 15)
    lines = len(code.splitlines())
    if lines > 300:
        score -= 10
    elif lines > 150:
        score -= 5
    return max(0, min(100, score))


def security_scan(code, language):
    findings = []
    for pattern, message in (
        (r"password\s*=\s*['\"]", "Hard-coded password detected."),
        (r"api[\-_]?key\s*=\s*['\"]", "Possible hard-coded API key detected."),
        (r"eval\s*\(", "Use of eval() can execute untrusted input."),
        (r"exec\s*\(", "Use of exec() can execute dynamic code."),
    ):
        if re.search(pattern, code, re.I):
            findings.append(message)
    return findings


def should_run_advanced_analysis(code, language):
    if not ENABLE_OLLAMA or len(code) > MAX_AI_CODE_LENGTH:
        return False
    if canonical_language(language) != "python":
        return True

    lower = code.lower()
    keywords = (
        "class ", "inheritance", "super(", "polymorphism", "bfs", "dfs",
        "graph", "adjacency", "thread", "lock", "mutex", "race condition",
        "requests.", "session.", "malloc(", "free(", "pointer",
        "linked list", "tree", "api",
    )
    if any(keyword in lower for keyword in keywords):
        return True

    structural = (
        "if ", "elif ", "else:", "for ", "while ",
        "return ", "try:", "except",
    )
    return (
        len(code) >= 250
        and sum(lower.count(token) for token in structural) >= 3
    )


def normalize_advanced_result(result, original_code):
    if not isinstance(result, dict):
        return {
            "detected": False,
            "category": "NONE",
            "severity": "NONE",
            "bug": "",
            "explanation": "",
            "root_cause": "",
            "suggested_fix": "",
            "corrected_code": "",
            "correction_verified": False,
            "evidence": [],
        }

    return {
        "detected": bool(result.get("detected", False)),
        "category": str(result.get("category", "NONE") or "NONE").strip(),
        "severity": normalize_severity(result.get("severity", "NONE")),
        "bug": str(result.get("bug", "") or "").strip(),
        "explanation": str(result.get("explanation", "") or "").strip(),
        "root_cause": str(result.get("root_cause", "") or "").strip(),
        "suggested_fix": str(result.get("suggested_fix", "") or "").strip(),
        "corrected_code": clean_corrected_code(
            result.get("corrected_code", ""),
        ),
        "correction_verified": False,
        "evidence": result.get("evidence", []) or [],
    }


def verify_advanced_correction(original, corrected, language, category):
    if not corrected or corrected.strip() == original.strip():
        return False

    if language.lower() == "python":
        try:
            ast.parse(corrected)
        except SyntaxError:
            return False

        if category.lower() == "recursion":
            tree = ast.parse(corrected)
            recursive = [
                n
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and _function_calls_self(n)
            ]
            if not recursive:
                return False
            if not any(
                isinstance(n, (ast.If, ast.Match))
                for fn in recursive
                for n in ast.walk(fn)
            ):
                return False
    else:
        validation = run_local_code_execution(corrected, language)
        if (
            validation.get("supported")
            and validation.get("status") == "success"
        ):
            return True

        pairs = {"(": ")", "[": "]", "{": "}"}
        stack = []
        for char in corrected:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack or pairs[stack.pop()] != char:
                    return False
        if stack:
            return False

    return True


# ============================================================
# FUNCTION SIGNATURES / TEST CASES
# ============================================================

def detect_function_names(code):
    names = []
    for pattern in (
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    ):
        names.extend(match.group(1) for match in re.finditer(pattern, code))
    return list(dict.fromkeys(names))


def detect_function_signatures(code, language=None):
    sigs = []
    language = canonical_language(language) if language else None

    if language in (None, "python"):
        for match in re.finditer(
            r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", code,
        ):
            params = _parse_param_list(match.group(2))
            sigs.append((match.group(1), params, "python"))

    if language in (None, "javascript"):
        for match in re.finditer(
            r"\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(([^)]*)\)", code,
        ):
            params = _parse_param_list(match.group(2))
            sigs.append((match.group(1), params, "javascript"))

        for match in re.finditer(
            r"\b(?:const|let|var)\s+"
            r"([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
            r"\(([^)]*)\)\s*=>",
            code,
        ):
            params = _parse_param_list(match.group(2))
            sigs.append((match.group(1), params, "javascript"))

        for match in re.finditer(
            r"\b(?:const|let|var)\s+"
            r"([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
            r"([A-Za-z_$][A-Za-z0-9_$]*)\s*=>",
            code,
        ):
            sigs.append(
                (match.group(1), [match.group(2)], "javascript")
            )

    seen = set()
    unique = []
    for name, params, lang in sigs:
        key = (name, tuple(params), lang)
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, params, lang))

    return unique


def generate_recursion_test_cases(function_name, body):
    name = function_name.lower()

    if "factorial" in name:
        return [
            {"name": "Base Case: 0", "input": f"{function_name}(0)", "expected_output": "1"},
            {"name": "Base Case: 1", "input": f"{function_name}(1)", "expected_output": "1"},
            {"name": "Typical Value", "input": f"{function_name}(5)", "expected_output": "120"},
            {"name": "Moderate Value", "input": f"{function_name}(10)", "expected_output": "3628800"},
        ]

    if "fibonacci" in name or "fib" in name:
        return [
            {"name": "Base Case: 0", "input": f"{function_name}(0)", "expected_output": "0"},
            {"name": "Base Case: 1", "input": f"{function_name}(1)", "expected_output": "1"},
            {"name": "Typical Value", "input": f"{function_name}(5)", "expected_output": "5"},
            {"name": "Moderate Value", "input": f"{function_name}(10)", "expected_output": "55"},
        ]

    return [
        {"name": "Base Case", "input": f"{function_name}(0)", "expected_output": "Function should terminate at its base case."},
        {"name": "Small Input", "input": f"{function_name}(1)", "expected_output": "Function should terminate correctly."},
        {"name": "Typical Input", "input": f"{function_name}(5)", "expected_output": "Function should complete without infinite recursion."},
        {"name": "Moderate Input", "input": f"{function_name}(10)", "expected_output": "Function should complete within normal resource limits."},
    ]


def _default_argument(param_name, scenario):
    name = param_name.lower()

    string_like = (
        "name", "text", "str", "string", "title",
        "label", "message", "msg",
    )
    list_like = ("list", "arr", "array", "items", "values", "nums")
    bool_like = ("flag", "bool", "enabled", "active", "valid")

    if scenario == "zero":
        if any(k in name for k in string_like):
            return '""'
        if any(k in name for k in list_like):
            return "[]"
        if any(k in name for k in bool_like):
            return "false"
        return "0"

    if scenario == "boundary":
        if any(k in name for k in string_like):
            return '"a"'
        if any(k in name for k in list_like):
            return "[]"
        if any(k in name for k in bool_like):
            return "true"
        return "1"

    if any(k in name for k in string_like):
        return '"example"'
    if any(k in name for k in list_like):
        return "[1, 2, 3]"
    if any(k in name for k in bool_like):
        return "true"
    if any(
        k in name for k in
        ("price", "amount", "value", "cost", "total", "sum")
    ):
        return "10"
    if any(
        k in name for k in
        ("quantity", "count", "qty", "num", "number")
    ):
        return "5"

    return "1"


def _build_argument_list(params, scenario):
    return [_default_argument(p, scenario) for p in params]


def generate_test_cases(code, language, advanced_analysis=None):
    if not code:
        return []

    language = canonical_language(language)

    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError:
            tree = None

        if tree:
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and _function_calls_self(node)
                ):
                    return generate_recursion_test_cases(
                        node.name,
                        ast.get_source_segment(code, node) or "",
                    )

    sigs = detect_function_signatures(code, language)
    if not sigs:
        return []

    name, params, _lang = sigs[0]

    if not params:
        return [
            {
                "name": "Typical Call",
                "input": f"{name}()",
                "expected_output": (
                    "Verify the function returns the expected result."
                ),
            },
        ]

    scenarios = [
        ("Typical Input", "typical"),
        ("Zero Values", "zero"),
        ("Boundary Values", "boundary"),
    ]

    return [
        {
            "name": label,
            "input": (
                f"{name}("
                + ", ".join(_build_argument_list(params, kind))
                + ")"
            ),
            "expected_output": (
                f"Verify {name} handles {label.lower()}."
            ),
        }
        for label, kind in scenarios
    ]


# ============================================================
# RESULT BUILDING
# ============================================================

def _make_specific_explanation(language, issue_text):
    lower = issue_text.lower()

    if "execution check failed" in lower:
        detail = (
            issue_text.split(":", 1)[1].strip()
            if ":" in issue_text else issue_text
        )
        return (
            f"The {language.title()} code failed the local execution "
            f"check. Runtime output: {detail}"
        )

    if "unmatched" in lower and "brace" in lower:
        return (
            f"The {language.title()} code has unbalanced curly braces — "
            "an opening '{' has no matching '}'."
        )

    if "unmatched" in lower and "parenthes" in lower:
        return (
            f"The {language.title()} code has unbalanced parentheses — "
            "an opening '(' has no matching ')'."
        )

    if "unmatched" in lower and "bracket" in lower:
        return (
            f"The {language.title()} code has unbalanced square brackets — "
            "an opening '[' has no matching ']'."
        )

    if "off-by-one" in lower:
        return (
            f"The {language.title()} code contains an off-by-one error in "
            "a loop. The loop condition uses '<=' with a length expression, "
            "which causes an out-of-bounds access on the final iteration."
        )

    if "syntax error" in lower or "syntaxerror" in lower:
        return f"The {language.title()} code contains a syntax error: {issue_text}"

    if "referenceerror" in lower:
        return f"The {language.title()} code has a runtime reference error: {issue_text}"

    if "compile error" in lower or "compileerror" in lower:
        return f"The {language.title()} code failed to compile: {issue_text}"

    return f"The {language.title()} static analyzer reported: {issue_text}"


def _make_specific_root_cause(language, issue_text):
    lower = issue_text.lower()

    if "execution check failed" in lower:
        if "referenceerror" in lower:
            return (
                "An identifier was used at runtime without being declared. "
                "This is usually caused by a typo in a variable name."
            )
        if "typeerror" in lower:
            return "An operation was performed on a value of an incompatible type."
        if "rangeerror" in lower:
            return "A value was used outside its allowed range."
        return "The submitted code failed at runtime."

    if "unmatched" in lower and "brace" in lower:
        return "An opening curly brace '{' was never closed."

    if "unmatched" in lower and "parenthes" in lower:
        return "An opening parenthesis '(' was never closed."

    if "unmatched" in lower and "bracket" in lower:
        return "An opening square bracket '[' was never closed."

    if "off-by-one" in lower:
        return "The loop condition '<=' includes one index past the end of the collection."

    if "syntax error" in lower or "syntaxerror" in lower:
        return "The source code violates the language's grammar rules."

    return f"The root cause is the reported issue: {issue_text}"


def build_local_result(
    code, language, static_issues, corrected_code, fix_messages,
    advanced_analysis=None, recursion_bug=None, runtime_error=None,
):
    static_issues = normalize_static_issues(static_issues)
    security = security_scan(code, language)
    complexity = calculate_complexity(code, language)
    quality = calculate_quality_score(code, static_issues)

    if runtime_error and runtime_error.get("detected"):
        return {
            "bug": runtime_error["bug"],
            "severity": "HIGH",
            "explanation": runtime_error["explanation"],
            "root_cause": runtime_error["root_cause"],
            "suggested_fix": runtime_error["suggested_fix"],
            "corrected_code": corrected_code,
            "improvements": (
                "Validate inputs and handle runtime failures "
                "before performing operations that can fail."
            ),
            "static_analysis": build_static_analysis(static_issues),
            "security_scan": security,
            "complexity": complexity,
            "quality_score": quality,
            "test_cases": generate_test_cases(corrected_code, language),
            "runtime_error": runtime_error["error_type"],
        }

    if recursion_bug and recursion_bug.get("detected"):
        name = recursion_bug.get("function_name", "the function")
        return {
            "bug": (
                f"The function '{name}' calls itself recursively "
                "without a valid base case, which will cause "
                "infinite recursion."
            ),
            "severity": "CRITICAL",
            "explanation": (
                f"The function '{name}' calls itself but has no "
                "branch that terminates the recursion."
            ),
            "root_cause": "Missing base case in a recursive function.",
            "suggested_fix": (
                "Add a base-case guard and make each recursive "
                "call move toward that base case."
            ),
            "corrected_code": corrected_code,
            "improvements": (
                "Always include an explicit base case and ensure "
                "recursive calls progress toward it."
            ),
            "static_analysis": build_static_analysis(static_issues),
            "security_scan": security,
            "complexity": complexity,
            "quality_score": quality,
            "test_cases": generate_test_cases(corrected_code, language),
        }

    if advanced_analysis and advanced_analysis.get("detected"):
        return {
            "bug": (
                advanced_analysis.get("bug")
                or "Advanced logic issue detected."
            ),
            "severity": advanced_analysis.get("severity", "MEDIUM"),
            "explanation": (
                advanced_analysis.get("explanation")
                or "An advanced semantic issue was detected."
            ),
            "root_cause": (
                advanced_analysis.get("root_cause")
                or "See the advanced analysis evidence."
            ),
            "suggested_fix": (
                advanced_analysis.get("suggested_fix")
                or "Review the corrected code."
            ),
            "corrected_code": corrected_code,
            "improvements": (
                "Review the advanced analysis and add regression tests."
            ),
            "static_analysis": build_static_analysis(static_issues),
            "security_scan": security,
            "complexity": complexity,
            "quality_score": quality,
            "test_cases": generate_test_cases(
                code, language, advanced_analysis,
            ),
            "advanced_analysis": advanced_analysis,
            "advanced_bug_detected": True,
            "advanced_category": advanced_analysis.get("category", "NONE"),
            "advanced_severity": advanced_analysis.get("severity", "NONE"),
            "advanced_correction_applied": bool(
                advanced_analysis.get("correction_verified")
            ),
            "advanced_correction_verified": bool(
                advanced_analysis.get("correction_verified")
            ),
        }

    if language == "javascript":
        js_undefined = extract_js_undefined_variable(static_issues)

        if js_undefined:
            applied_fix = fix_messages[0] if fix_messages else ""

            if applied_fix:
                suggested = applied_fix
            else:
                suggested = (
                    f"Declare '{js_undefined}' before using it, or correct the "
                    "spelling to match an existing variable."
                )

            return {
                "bug": f"ReferenceError: '{js_undefined}' is not defined.",
                "severity": "HIGH",
                "explanation": (
                    f"The JavaScript code references the identifier "
                    f"'{js_undefined}' at runtime, but no binding for it "
                    "exists in the current scope. Node.js throws "
                    "ReferenceError when a name is used before it is "
                    "declared with let, const, var, or as a parameter."
                ),
                "root_cause": (
                    f"'{js_undefined}' is not in scope when it is executed. "
                    "This is almost always caused by a typo in a variable "
                    "name, or by using a name that was never declared."
                ),
                "suggested_fix": suggested,
                "corrected_code": corrected_code,
                "improvements": (
                    "Enable strict mode ('use strict') at the top of the file "
                    "and run ESLint with the no-undef rule to catch undefined "
                    "identifiers before runtime."
                ),
                "static_analysis": build_static_analysis(static_issues),
                "security_scan": security,
                "complexity": complexity,
                "quality_score": quality,
                "test_cases": generate_test_cases(corrected_code, language),
            }

    undefined = extract_undefined_variable(static_issues)

    if undefined:
        return {
            "bug": f"undefined name '{undefined}'",
            "severity": "HIGH",
            "explanation": (
                f"The variable '{undefined}' is used but "
                "is not defined in the available scope."
            ),
            "root_cause": (
                f"The name '{undefined}' is referenced "
                "without a valid definition."
            ),
            "suggested_fix": (
                fix_messages[0]
                if fix_messages
                else (
                    f"Replace '{undefined}' with the "
                    "correct defined variable."
                )
            ),
            "corrected_code": corrected_code,
            "improvements": (
                "Use clear variable names and verify "
                "function arguments before use."
            ),
            "static_analysis": build_static_analysis(static_issues),
            "security_scan": security,
            "complexity": complexity,
            "quality_score": quality,
            "test_cases": generate_test_cases(corrected_code, language),
        }

    if static_issues:
        first_issue = static_issues[0]
        explanation = _make_specific_explanation(language, first_issue)
        root_cause = _make_specific_root_cause(language, first_issue)

        return {
            "bug": first_issue,
            "severity": (
                "HIGH" if has_serious_static_issue(static_issues)
                else "MEDIUM"
            ),
            "explanation": explanation,
            "root_cause": root_cause,
            "suggested_fix": (
                fix_messages[0]
                if fix_messages
                else "Fix the reported static-analysis issue."
            ),
            "corrected_code": corrected_code,
            "improvements": (
                "Run static analysis before executing the program."
            ),
            "static_analysis": build_static_analysis(static_issues),
            "security_scan": security,
            "complexity": complexity,
            "quality_score": quality,
            "test_cases": generate_test_cases(corrected_code, language),
        }

    return {
        "bug": "No bug detected.",
        "severity": "NONE",
        "explanation": (
            "The provided code does not contain any obvious "
            "programming errors based on the available local checks."
        ),
        "root_cause": "No root cause because no bug was detected.",
        "suggested_fix": "No fix is necessary.",
        "corrected_code": corrected_code,
        "improvements": "None",
        "static_analysis": "No static analysis issues detected.",
        "security_scan": security,
        "complexity": complexity,
        "quality_score": quality,
        "test_cases": generate_test_cases(corrected_code, language),
    }


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_code(code, language):
    if not code or not str(code).strip():
        raise ValueError("Code cannot be empty.")

    if not language or not str(language).strip():
        raise ValueError("Programming language is required.")

    code = str(code)
    language = canonical_language(language)

    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(
            ["Python", "JavaScript", "Java", "C", "C++", "HTML", "CSS"]
        )
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Currently supported: {supported}."
        )

    if len(code) > MAX_AI_CODE_LENGTH:
        raise ValueError(
            "Code is too large. Please keep the code "
            "below 15,000 characters."
        )

    print(f"Analyzing {language} code ({len(code)} characters)...")

    runtime_error = detect_local_runtime_error(code, language)

    if runtime_error:
        print(
            "FAST PATH:",
            runtime_error["error_type"],
            "detected locally.",
        )

    recursion_bug = {"detected": False}
    corrected_code = code
    fix_messages = []
    recursion_fix_succeeded = False

    if language == "python" and not runtime_error:
        recursion_bug = detect_recursion_without_base_case(code)

        if recursion_bug.get("detected"):
            print(
                "FAST PATH: recursion bug detected "
                "locally; Ollama skipped."
            )
            corrected_code, message = fix_recursion_without_base_case(
                code, recursion_bug,
            )
            if message:
                recursion_fix_succeeded = True
                fix_messages.append(message)

    execution_result = None
    static_start = time.time()

    static_issues = normalize_static_issues(
        run_static_analysis(code, language),
    )

    if language == "python":
        static_issues = filter_false_positive_undefined_issues(
            code, static_issues,
        )

        if not extract_undefined_variable(static_issues):
            static_issues.extend(
                issue
                for issue in build_scope_aware_undefined_issues(code)
                if issue not in static_issues
            )

        static_issues.extend(
            issue for issue in run_pyflakes(code)
            if issue not in static_issues
        )

        static_issues = filter_false_positive_undefined_issues(
            code, static_issues,
        )

    print(
        f"Static analysis time: "
        f"{time.time() - static_start:.2f} seconds"
    )

    if language != "python":
        execution_start = time.time()
        execution_result = run_local_code_execution(code, language)
        print(
            f"{language} execution/validation time: "
            f"{time.time() - execution_start:.2f} seconds"
        )

        execution_issue = execution_issue_text(execution_result, language)
        if execution_issue and execution_issue not in static_issues:
            static_issues.append(execution_issue)

    if runtime_error:
        corrected_code, runtime_fix_message = apply_safe_runtime_fix(
            code, runtime_error, language,
        )
        if runtime_fix_message:
            fix_messages.append(runtime_fix_message)
    elif not recursion_bug.get("detected"):
        corrected_code, automatic_messages = apply_automatic_fixes(
            code, language, static_issues, execution_result,
        )
        fix_messages.extend(automatic_messages)

    corrected_static_issues = []

    if corrected_code.strip() != code.strip():
        corrected_static_issues = normalize_static_issues(
            run_static_analysis(corrected_code, language),
        )

        if language == "python":
            corrected_static_issues = (
                filter_false_positive_undefined_issues(
                    corrected_code, corrected_static_issues,
                )
            )
            corrected_static_issues.extend(
                issue
                for issue in build_scope_aware_undefined_issues(corrected_code)
                if issue not in corrected_static_issues
            )
            corrected_static_issues.extend(
                issue for issue in run_pyflakes(corrected_code)
                if issue not in corrected_static_issues
            )
            corrected_static_issues = (
                filter_false_positive_undefined_issues(
                    corrected_code, corrected_static_issues,
                )
            )

        corrected_validation = run_local_code_execution(
            corrected_code, language,
        )
        corrected_validation_issue = execution_issue_text(
            corrected_validation, language,
        )
        if (
            corrected_validation_issue
            and corrected_validation_issue not in corrected_static_issues
        ):
            corrected_static_issues.append(corrected_validation_issue)

    advanced = None
    execution_failed = bool(
        execution_result
        and execution_result.get("status") in {
            "compile_or_runtime_error", "validation_error", "timeout",
        }
    )

    if (
        ENABLE_OLLAMA
        and not runtime_error
        and not recursion_bug.get("detected")
        and (
            execution_failed
            or should_run_advanced_analysis(code, language)
        )
    ):
        ai_start = time.time()
        print("Starting advanced AI analysis (single Ollama request)...")

        try:
            advanced = normalize_advanced_result(
                run_advanced_analysis(code, language), code,
            )
            advanced_code = advanced.get("corrected_code", "")

            if advanced.get("detected") and advanced_code:
                verified = verify_advanced_correction(
                    code, advanced_code, language,
                    advanced.get("category", "NONE"),
                )
                advanced["correction_verified"] = verified

                if verified:
                    corrected_code = advanced_code
                    fix_messages.append(
                        "Advanced AI correction applied "
                        "and verified locally."
                    )

        except Exception as error:
            print("Advanced AI analysis error:", error)
            advanced = None

        print(
            f"Advanced AI time: "
            f"{time.time() - ai_start:.2f} seconds"
        )

    if language == "python":
        code_to_execute = (
            corrected_code
            if corrected_code.strip() != code.strip()
            else code
        )
        execution_result = run_local_code_execution(
            code_to_execute, language,
        )

    corrected_execution_result = None
    if (
        language != "python"
        and corrected_code.strip() != code.strip()
    ):
        corrected_execution_result = run_local_code_execution(
            corrected_code, language,
        )

    result = build_local_result(
        code=code,
        language=language,
        static_issues=static_issues,
        corrected_code=corrected_code.strip(),
        fix_messages=fix_messages,
        advanced_analysis=advanced,
        recursion_bug=recursion_bug,
        runtime_error=runtime_error,
    )

    result["execution"] = execution_result or {
        "supported": False,
        "status": "not_run",
        "error_type": None,
        "stdout": "",
        "stderr": "",
        "returncode": None,
    }

    if corrected_execution_result is not None:
        result["corrected_execution"] = corrected_execution_result

    if corrected_code.strip() != code.strip():
        result["execution_mode"] = "corrected_code_verified"
    else:
        result["execution_mode"] = "submitted_code_verified"

    result["automatic_fix"] = (
        " ".join(fix_messages)
        if fix_messages
        else "No automatic fix required."
    )

    if runtime_error:
        if corrected_code.strip() != code.strip():
            result["fix_status"] = "runtime_fix_applied"
        else:
            result["fix_status"] = "runtime_issue_detected_needs_review"
    elif recursion_bug.get("detected"):
        result["fix_status"] = (
            "recursion_fast_fix_applied"
            if recursion_fix_succeeded
            else "recursion_fast_fix_failed_needs_review"
        )
    elif advanced and advanced.get("correction_verified"):
        result["fix_status"] = "advanced_ai_applied"
    elif fix_messages:
        result["fix_status"] = "automatic_fix_applied"
    else:
        result["fix_status"] = "no_fix_required"

    if runtime_error:
        if (
            corrected_code.strip() != code.strip()
            and not corrected_static_issues
        ):
            result["post_fix_static_analysis"] = (
                "A safe automatic correction was applied "
                "and no remaining static-analysis issues "
                "were detected."
            )
        elif corrected_static_issues:
            result["post_fix_static_analysis"] = build_static_analysis(
                corrected_static_issues,
            )
        else:
            result["post_fix_static_analysis"] = (
                "No automatic runtime correction was applied "
                "because the exact intended application behavior "
                "is ambiguous. See the suggested fix."
            )
    elif recursion_bug.get("detected"):
        result["post_fix_static_analysis"] = (
            "The automatic recursion fix was applied and verified. "
            "No remaining static-analysis issues detected."
            if recursion_fix_succeeded
            else
            "The automatic recursion fix could not be applied. "
            "Please add a base case and make the recursive call "
            "progress toward it."
        )
    elif corrected_static_issues:
        result["post_fix_static_analysis"] = build_static_analysis(
            corrected_static_issues,
        )
    elif corrected_code.strip() != code.strip():
        if language == "javascript" and fix_messages:
            post_validation = run_local_code_execution(
                corrected_code, language,
            )
            post_issue = execution_issue_text(post_validation, language)
            if post_issue:
                result["post_fix_static_analysis"] = post_issue
            else:
                result["post_fix_static_analysis"] = (
                    "No remaining static-analysis issues detected."
                )
        else:
            result["post_fix_static_analysis"] = (
                "No remaining static-analysis issues detected."
            )
    else:
        result["post_fix_static_analysis"] = result.get(
            "static_analysis",
            "No static analysis issues detected.",
        )

    result["quality_score"] = calculate_quality_score(
        corrected_code,
        corrected_static_issues or static_issues,
    )

    result["test_cases"] = generate_test_cases(
        corrected_code, language, advanced,
    )

    result["raw"] = build_raw_report(result)

    print("TOTAL ANALYSIS COMPLETE")

    return result


# ============================================================
# REPORT FORMATTING
# ============================================================

def _format_execution_for_report(execution):
    if not isinstance(execution, dict):
        return "Not run."

    status = execution.get("status", "not_run")

    if status == "success":
        output = execution.get("stdout", "").strip()
        return (
            "SUCCESS\n"
            + (output if output else "Program completed successfully.")
        )

    if status == "disabled":
        return "Local execution is disabled."

    if status == "unavailable":
        return "UNAVAILABLE\n" + str(execution.get("stderr", ""))

    if status == "not_run":
        return "Not run."

    details = (
        execution.get("stderr")
        or execution.get("stdout")
        or "Unknown error."
    ).strip()

    return f"{status.upper()}\n{details}"


def build_raw_report(analysis):
    return f"""BUG DETECTED:

{analysis.get('bug', 'No bug detected.')}

SEVERITY:

{analysis.get('severity', 'NONE')}

EXPLANATION:

{analysis.get('explanation', '')}

ROOT CAUSE:

{analysis.get('root_cause', '')}

SUGGESTED FIX:

{analysis.get('suggested_fix', '')}

CORRECTED CODE:

{analysis.get('corrected_code', '')}

IMPROVEMENTS:

{analysis.get('improvements', 'None')}

STATIC ANALYSIS:

{analysis.get('static_analysis', 'No static analysis issues detected.')}

EXECUTION / VALIDATION:

{_format_execution_for_report(analysis.get('execution', {}))}

CORRECTED CODE EXECUTION / VALIDATION:

{_format_execution_for_report(analysis.get('corrected_execution', analysis.get('execution', {})))}""".strip()