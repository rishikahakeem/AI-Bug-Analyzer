import ast
import json
import os
import re

import requests


# ============================================================
# PERFORMANCE SETTINGS
# ============================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate"
)

MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2"
)

ADVANCED_TIMEOUT = int(
    os.getenv("ADVANCED_TIMEOUT", "15")
)

ADVANCED_MAX_TOKENS = int(
    os.getenv("ADVANCED_MAX_TOKENS", "450")
)

MAX_ADVANCED_CODE_LENGTH = 15000


# ============================================================
# PYTHON PATTERN DETECTION
# ============================================================

def detect_python_patterns(code):
    findings = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return findings

    classes = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]

    functions = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    # OOP
    if classes:
        findings.append("OOP")

    # Inheritance
    if any(cls.bases for cls in classes):
        findings.append("Inheritance")

    # Polymorphism heuristic
    method_map = {}
    for cls in classes:
        methods = {
            node.name
            for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for method in methods:
            method_map.setdefault(method, []).append(cls.name)

    if any(len(owners) >= 2 for owners in method_map.values()):
        findings.append("Polymorphism")

    # Recursion
    for function in functions:
        recursive = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == function.name
            for node in ast.walk(function)
        )
        if recursive:
            findings.append("Recursion")
            break

    # Graph algorithms
    lower = code.lower()
    graph_words = [
        "graph",
        "adjacency",
        "bfs",
        "dfs",
        "visited",
        "queue",
        "stack",
        "neighbors",
    ]
    if sum(word in lower for word in graph_words) >= 2:
        findings.append("Graph Algorithm")

    # Data structures
    structure_words = [
        "linked list",
        "tree",
        "heap",
        "deque",
        "stack",
        "queue",
        "dictionary",
        "hashmap",
    ]
    if any(word in lower for word in structure_words):
        findings.append("Data Structure")

    # Concurrency / race condition
    concurrency_words = [
        "thread",
        "threading",
        "asyncio",
        "lock",
        "mutex",
        "semaphore",
        "shared_data",
        "shared_counter",
    ]
    if any(word in lower for word in concurrency_words):
        findings.append("Race Condition")

    # Memory management
    memory_words = [
        "malloc",
        "calloc",
        "realloc",
        "free(",
        "delete ",
        "pointer",
        "memory leak",
        "garbage collection",
    ]
    if any(word in lower for word in memory_words):
        findings.append("Memory Management")

    # API / library misuse
    if any(word in lower for word in [
        "requests.",
        "urllib",
        "http",
        "api",
        "open(",
        "json.load",
        "json.loads",
    ]):
        findings.append("Library/API Misuse")

    # Logic/error-prone control flow
    if any(isinstance(node, (ast.If, ast.For, ast.While, ast.Try)) for node in ast.walk(tree)):
        findings.append("Logic Error")

    return list(dict.fromkeys(findings))


def detect_patterns(code, language):
    if language.lower() == "python":
        return detect_python_patterns(code)

    lower = code.lower()
    findings = []

    if "class " in lower:
        findings.append("OOP")
    if "extends " in lower or ": public " in lower or ": protected " in lower:
        findings.append("Inheritance")
    if "bfs" in lower or "dfs" in lower or "adjacency" in lower:
        findings.append("Graph Algorithm")
    if "thread" in lower or "mutex" in lower or "lock" in lower:
        findings.append("Race Condition")
    if "malloc(" in lower or "free(" in lower or "pointer" in lower:
        findings.append("Memory Management")
    if "api" in lower or "requests." in lower:
        findings.append("Library/API Misuse")

    return list(dict.fromkeys(findings))


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):
    if not text:
        return None

    text = str(text).strip()

    # Direct JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # JSON inside markdown fence
    fenced = re.search(
        r"```json\s*(\{.*?\})\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # First balanced object
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:index + 1]
                    try:
                        data = json.loads(candidate)
                        if isinstance(data, dict):
                            return data
                    except json.JSONDecodeError:
                        break

    return None


# ============================================================
# PYTHON CORRECTION VALIDATION
# ============================================================

def validate_python_code(code):
    if not code:
        return False
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def validate_recursion_correction(code, original_code):
    if not validate_python_code(code):
        return False

    try:
        original_tree = ast.parse(original_code)
        corrected_tree = ast.parse(code)
    except SyntaxError:
        return False

    recursive_names = []
    for node in ast.walk(original_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == node.name
                for child in ast.walk(node)
            ):
                recursive_names.append(node.name)

    if not recursive_names:
        return True

    for name in recursive_names:
        for node in ast.walk(corrected_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != name:
                continue

            has_recursive_call = any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == name
                for child in ast.walk(node)
            )
            has_branch = any(
                isinstance(child, ast.If)
                for child in ast.walk(node)
            )

            if has_recursive_call and has_branch:
                return True

    return False


def validate_correction(original_code, corrected_code, language, category):
    if not corrected_code:
        return False

    if corrected_code.strip() == original_code.strip():
        return False

    if language.lower() == "python":
        if category.lower() == "recursion":
            return validate_recursion_correction(
                corrected_code,
                original_code
            )
        return validate_python_code(corrected_code)

    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = []

    for char in corrected_code:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack:
                return False
            opening = stack.pop()
            if pairs[opening] != char:
                return False

    return not stack


# ============================================================
# ONE-CALL OLLAMA ANALYSIS
# ============================================================

def build_prompt(code, language, patterns):
    pattern_text = ", ".join(patterns) if patterns else "general logic"

    return f"""
You are the semantic layer of a software bug analyzer.

Programming language: {language}
Potential code areas: {pattern_text}

Analyze the COMPLETE source code.

Return ONLY valid JSON with exactly these keys:

{{
  "detected": true,
  "category": "Recursion",
  "severity": "CRITICAL",
  "confidence": 0.95,
  "bug": "...",
  "explanation": "...",
  "root_cause": "...",
  "suggested_fix": "...",
  "corrected_code": "...",
  "evidence": ["..."]
}}

Rules:
- Detect only genuine programming bugs.
- Do not invent a bug merely because code could be improved.
- Use severity exactly: CRITICAL, HIGH, MEDIUM, LOW, NONE.
- If no genuine bug exists, use detected=false, category=NONE, severity=NONE.
- corrected_code must be the COMPLETE corrected source code.
- Keep working code unchanged when no fix is required.
- Never invent arbitrary variables or values.
- For recursion, verify a valid terminating/base case.
- For inheritance/polymorphism, check method behavior and super() usage.
- For graph algorithms, check visited handling, queue/stack behavior, and traversal logic.
- For data structures, check indexing, mutation, empty cases, and invariants.
- For race conditions, check shared mutable state and synchronization.
- For memory management, check allocation/deallocation and ownership.
- For library/API use, check required arguments, error/status handling, and context management.
- For logic errors, check conditions, loop bounds, return values, and state transitions.

Source code:
----------------
{code}
----------------
""".strip()


def request_ollama(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.1,
                "num_predict": ADVANCED_MAX_TOKENS,
            },
        },
        timeout=ADVANCED_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}"
        )

    data = response.json()
    text = data.get("response", "")

    if not text:
        raise RuntimeError("Ollama returned an empty response.")

    return text.strip()


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def run_advanced_analysis(code, language):
    if not code or len(code) > MAX_ADVANCED_CODE_LENGTH:
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

    patterns = detect_patterns(code, language)

    print(
        "ADVANCED PATTERNS:",
        patterns
    )

    if not patterns:
        return {
            "detected": False,
            "category": "NONE",
            "severity": "NONE",
            "bug": "",
            "explanation": "No advanced semantic pattern requires AI analysis.",
            "root_cause": "",
            "suggested_fix": "",
            "corrected_code": "",
            "correction_verified": False,
            "evidence": [],
        }

    prompt = build_prompt(
        code,
        language,
        patterns
    )

    print("ADVANCED OLLAMA: one request only")

    raw = request_ollama(prompt)
    parsed = extract_json(raw)

    if not parsed:
        return {
            "detected": False,
            "category": "NONE",
            "severity": "NONE",
            "bug": "",
            "explanation": "The AI response could not be parsed safely.",
            "root_cause": "",
            "suggested_fix": "",
            "corrected_code": "",
            "correction_verified": False,
            "evidence": [],
        }

    category = str(
        parsed.get("category", "NONE") or "NONE"
    ).strip()

    corrected_code = str(
        parsed.get("corrected_code", "") or ""
    ).strip()

    verified = False

    if bool(parsed.get("detected")) and corrected_code:
        verified = validate_correction(
            code,
            corrected_code,
            language,
            category
        )

    return {
        "detected": bool(parsed.get("detected", False)),
        "category": category,
        "severity": str(parsed.get("severity", "NONE") or "NONE").upper(),
        "confidence": parsed.get("confidence", 0),
        "bug": str(parsed.get("bug", "") or "").strip(),
        "explanation": str(parsed.get("explanation", "") or "").strip(),
        "root_cause": str(parsed.get("root_cause", "") or "").strip(),
        "suggested_fix": str(parsed.get("suggested_fix", "") or "").strip(),
        "corrected_code": corrected_code if verified else "",
        "correction_verified": verified,
        "evidence": parsed.get("evidence", []) or [],
    }
