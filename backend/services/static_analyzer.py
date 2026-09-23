import ast
import builtins
import re

SUPPORTED_LANGUAGES = {"python", "javascript", "java", "c", "c++", "cpp", "html", "css"}
PYTHON_BUILTINS = set(dir(builtins))

def normalize_language(language):
    if not language: return ""
    language = str(language).strip().lower()
    aliases = {"py": "python", "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript", "cpp": "c++", "cc": "c++", "h": "c", "hpp": "c++", "htm": "html"}
    return aliases.get(language, language)

def unique_issues(issues):
    result = []
    for issue in issues:
        issue = str(issue).strip()
        if issue and issue not in result: result.append(issue)
    return result

def create_analysis_result(issues, bug_detected=False, severity="NONE", bug_type=None):
    clean_issues = unique_issues(issues)
    return {
        "issues": clean_issues,
        "bug_detected": bug_detected or len(clean_issues) > 0,
        "severity": severity if len(clean_issues) > 0 else "NONE",
        "bug_type": bug_type if len(clean_issues) > 0 else None
    }

def collect_target_names(target, defined):
    if isinstance(target, ast.Name): defined.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts: collect_target_names(element, defined)
    elif isinstance(target, ast.Starred): collect_target_names(target.value, defined)

def collect_python_definitions(tree):
    defined = set()
    wildcard_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname: defined.add(alias.asname)
                else: defined.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    wildcard_import = True
                    continue
                if alias.asname: defined.add(alias.asname)
                else: defined.add(alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            for decorator in node.decorator_list: collect_target_names(decorator, defined)
            for argument in node.args.posonlyargs: defined.add(argument.arg)
            for argument in node.args.args: defined.add(argument.arg)
            for argument in node.args.kwonlyargs: defined.add(argument.arg)
            if node.args.vararg: defined.add(node.args.vararg.arg)
            if node.args.kwarg: defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.ClassDef): defined.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets: collect_target_names(target, defined)
        elif isinstance(node, ast.AnnAssign): collect_target_names(node.target, defined)
        elif isinstance(node, ast.AugAssign): collect_target_names(node.target, defined)
        elif isinstance(node, (ast.For, ast.AsyncFor)): collect_target_names(node.target, defined)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars: collect_target_names(item.optional_vars, defined)
        elif isinstance(node, ast.AsyncWith):
            for item in node.items:
                if item.optional_vars: collect_target_names(item.optional_vars, defined)
        elif isinstance(node, ast.ExceptHandler):
            if node.name: defined.add(node.name)
        elif isinstance(node, ast.NamedExpr): collect_target_names(node.target, defined)
    return defined, wildcard_import

def collect_local_definitions(body):
    defined = set()
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): defined.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname: defined.add(alias.asname)
                else: defined.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    if alias.asname: defined.add(alias.asname)
                    else: defined.add(alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets: collect_target_names(target, defined)
        elif isinstance(node, ast.AnnAssign): collect_target_names(node.target, defined)
        elif isinstance(node, ast.AugAssign): collect_target_names(node.target, defined)
        elif isinstance(node, (ast.For, ast.AsyncFor)): collect_target_names(node.target, defined)
        elif isinstance(node, ast.NamedExpr): collect_target_names(node.target, defined)
    return defined

def analyze_python_syntax(code):
    try:
        tree = ast.parse(code, filename="submitted_code.py")
        return tree, []
    except SyntaxError as error:
        line_number = error.lineno or 0
        message = f"Syntax error on line {line_number}: {error.msg}"
        return None, [message]
    except Exception as error:
        return None, [f"Python parsing error: {error}"]

def detect_off_by_one_bugs(code, language):
    issues = []
    code = str(code or "")

    if language in {"javascript", "java", "c", "c++"}:
        size_var_names = (
            "size", "length", "count", "len", "max", "limit",
            "capacity", "cap", "array_size", "arr_size",
            "items_count", "item_count", "element_count", "elem_count",
            "n", "total_size", "total"
        )

        prop_pattern = re.compile(
            r"for\s*\(\s*"
            r"(?:var|let|int|long|size_t|auto|unsigned\s+int|unsigned)?\s*\w+\s*=\s*0\s*;\s*"
            r"\w+\s*<=\s*"
            r"([\w\.\[\]]+?)\s*"
            r"(?:\.length|\.size\s*\(\s*\)|\.size)\b",
            re.IGNORECASE
        )
        for match in prop_pattern.finditer(code):
            target = match.group(1)
            line_num = code[:match.start()].count("\n") + 1
            issues.append(
                f"Possible off-by-one error: loop uses '<=' with "
                f"{target}.length — will access index {target}.length, which is "
                f"undefined. Use '<' instead of '<='. (line {line_num})"
            )

        size_var_pattern = re.compile(
            r"for\s*\(\s*"
            r"(?:var|let|int|long|size_t|auto|unsigned\s+int|unsigned)?\s*\w+\s*=\s*0\s*;\s*"
            r"\w+\s*<=\s*(\w+)\s*;",
            re.IGNORECASE
        )
        for match in size_var_pattern.finditer(code):
            var = match.group(1)
            if var.lower() not in size_var_names:
                continue
            line_num = code[:match.start()].count("\n") + 1
            msg = (
                f"Possible off-by-one error: loop uses '<=' with '{var}' — "
                f"if '{var}' is a collection length, the last iteration will "
                f"access an out-of-bounds index. Use '<' instead of '<='. "
                f"(line {line_num})"
            )
            if not any(var in existing for existing in issues):
                issues.append(msg)

    elif language == "python":
        py_pattern = re.compile(
            r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(\s*([\w\.\[\]]+)\s*\)\s*\+\s*1\s*\)",
            re.IGNORECASE
        )
        for match in py_pattern.finditer(code):
            target = match.group(1)
            line_num = code[:match.start()].count("\n") + 1
            issues.append(
                f"Possible off-by-one error: range(len({target}) + 1) will "
                f"access index {target}.length which is out of bounds. "
                f"Use range(len({target})) instead. (line {line_num})"
            )

    return issues

class PythonUndefinedNameVisitor(ast.NodeVisitor):
    def __init__(self, global_defined, wildcard_import):
        self.global_defined = set(global_defined)
        self.wildcard_import = wildcard_import
        self.issues = []
        self.local_scopes = []
        self.checked_names = set()

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Load): return
        name = node.id
        if name in PYTHON_BUILTINS: return
        if name in self.global_defined: return
        for scope in reversed(self.local_scopes):
            if name in scope: return
        if self.wildcard_import: return
        key = (name, getattr(node, "lineno", 0))
        if key in self.checked_names: return
        self.checked_names.add(key)
        self.issues.append(f"Possible undefined variable: '{name}' (line {getattr(node, 'lineno', 0)})")

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list: self.visit(decorator)
        for default in node.args.defaults: self.visit(default)
        for default in node.args.kw_defaults:
            if default: self.visit(default)
        if node.returns: self.visit(node.returns)

        local_defined = set()
        for argument in node.args.posonlyargs: local_defined.add(argument.arg)
        for argument in node.args.args: local_defined.add(argument.arg)
        for argument in node.args.kwonlyargs: local_defined.add(argument.arg)
        if node.args.vararg: local_defined.add(node.args.vararg.arg)
        if node.args.kwarg: local_defined.add(node.args.kwarg.arg)
        local_defined.update(collect_local_definitions(node.body))

        self.local_scopes.append(local_defined)
        for statement in node.body: self.visit(statement)
        self.local_scopes.pop()

    def visit_AsyncFunctionDef(self, node): self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        for decorator in node.decorator_list: self.visit(decorator)
        for base in node.bases: self.visit(base)
        for keyword in node.keywords: self.visit(keyword)
        class_defined = set()
        class_defined.update(collect_local_definitions(node.body))
        self.local_scopes.append(class_defined)
        for statement in node.body: self.visit(statement)
        self.local_scopes.pop()

def run_python_static_analysis(code):
    tree, syntax_issues = analyze_python_syntax(code)
    if syntax_issues:
        return create_analysis_result(issues=syntax_issues, bug_detected=True, severity="HIGH", bug_type="Syntax Error")
    if tree is None:
        return create_analysis_result([])

    defined, wildcard_import = collect_python_definitions(tree)
    visitor = PythonUndefinedNameVisitor(global_defined=defined, wildcard_import=wildcard_import)
    visitor.visit(tree)
    issues = unique_issues(visitor.issues)

    off_by_one = detect_off_by_one_bugs(code, "python")
    issues.extend(off_by_one)

    if issues:
        has_high = any("off-by-one" in issue.lower() for issue in issues)
        return create_analysis_result(
            issues=issues,
            bug_detected=True,
            severity="HIGH" if has_high else "MEDIUM",
            bug_type="Static Analysis Issue"
        )
    return create_analysis_result([])

def run_javascript_static_analysis(code):
    issues = []
    if code.count("{") != code.count("}"): issues.append("Possible syntax error: unmatched curly braces.")
    if code.count("(") != code.count(")"): issues.append("Possible syntax error: unmatched parentheses.")
    if code.count("[") != code.count("]"): issues.append("Possible syntax error: unmatched square brackets.")

    declared = set(re.findall(r"\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)", code))
    declared.update(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", code))
    declared.update(re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", code))
    declared.update(re.findall(r"\bimport\s+([A-Za-z_$][\w$]*)", code))

    javascript_globals = {
        "console", "window", "document", "globalThis", "Math", "JSON",
        "Array", "Object", "String", "Number", "Boolean", "Date", "Promise",
        "Error", "TypeError", "RangeError", "ReferenceError", "SyntaxError",
        "Set", "Map", "WeakSet", "WeakMap", "RegExp", "Symbol",
        "Proxy", "Reflect", "Atomics", "SharedArrayBuffer", "ArrayBuffer",
        "DataView", "Int8Array", "Uint8Array", "Int16Array", "Uint16Array",
        "Int32Array", "Uint32Array", "Float32Array", "Float64Array",
        "BigInt64Array", "BigUint64Array", "BigInt",
        "parseInt", "parseFloat", "isNaN", "isFinite", "encodeURI",
        "decodeURI", "encodeURIComponent", "decodeURIComponent", "eval",
        "require", "module", "exports", "process", "setTimeout",
        "setInterval", "clearTimeout", "clearInterval", "queueMicrotask",
        "structuredClone", "fetch", "URL", "URLSearchParams", "FormData",
        "Blob", "File", "FileReader", "localStorage", "sessionStorage",
        "alert", "confirm", "prompt", "atob", "btoa",
        "undefined", "null", "true", "false", "NaN", "Infinity",
    }

    javascript_keywords = {
        "if", "else", "for", "while", "do", "switch", "case", "default",
        "break", "continue", "return", "function", "class", "extends",
        "new", "delete", "typeof", "instanceof", "in", "of", "void",
        "throw", "try", "catch", "finally", "yield", "await", "async",
        "this", "super", "static", "get", "set", "import", "export",
    }

    lines = code.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped: continue
        if stripped.startswith("//"): continue

        for match in re.finditer(
            r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(",
            stripped
        ):
            name = match.group(1)
            if name in declared: continue
            if name in javascript_globals: continue
            if name in javascript_keywords: continue
            issues.append(f"Possible undefined function: '{name}' (line {index})")

    off_by_one = detect_off_by_one_bugs(code, "javascript")
    issues.extend(off_by_one)

    return create_analysis_result(
        issues=issues,
        bug_detected=len(issues) > 0,
        severity="HIGH" if any(
            "syntax error" in issue.lower()
            or "unmatched" in issue.lower()
            or "off-by-one" in issue.lower()
            for issue in issues
        ) else "MEDIUM",
        bug_type="JavaScript Static Analysis Issue"
    )

def run_java_static_analysis(code):
    issues = []
    if code.count("{") != code.count("}"): issues.append("Possible syntax error: unmatched curly braces.")
    if code.count("(") != code.count(")"): issues.append("Possible syntax error: unmatched parentheses.")
    if code.count("[") != code.count("]"): issues.append("Possible syntax error: unmatched square brackets.")

    off_by_one = detect_off_by_one_bugs(code, "java")
    issues.extend(off_by_one)

    return create_analysis_result(
        issues=issues,
        bug_detected=len(issues) > 0,
        severity="HIGH",
        bug_type="Java Static Analysis Issue"
    )

def run_c_cpp_static_analysis(code):
    issues = []
    if code.count("{") != code.count("}"): issues.append("Possible syntax error: unmatched curly braces.")
    if code.count("(") != code.count(")"): issues.append("Possible syntax error: unmatched parentheses.")
    if code.count("[") != code.count("]"): issues.append("Possible syntax error: unmatched square brackets.")

    off_by_one = detect_off_by_one_bugs(code, "c++")
    issues.extend(off_by_one)

    return create_analysis_result(
        issues=issues,
        bug_detected=len(issues) > 0,
        severity="HIGH",
        bug_type="C/C++ Static Analysis Issue"
    )

def run_html_static_analysis(code):
    issues = []
    if code.count("<html") > code.count("</html"): issues.append("Possible HTML issue: missing </html> closing tag.")
    if code.count("<body") > code.count("</body"): issues.append("Possible HTML issue: missing </body> closing tag.")
    if code.count("<head") > code.count("</head"): issues.append("Possible HTML issue: missing </head> closing tag.")
    return create_analysis_result(issues=issues, bug_detected=len(issues) > 0, severity="MEDIUM", bug_type="HTML Syntax Issue")

def run_css_static_analysis(code):
    issues = []
    if code.count("{") != code.count("}"): issues.append("Possible CSS syntax error: unmatched curly braces.")
    if code.count("(") != code.count(")"): issues.append("Possible CSS syntax error: unmatched parentheses.")
    return create_analysis_result(issues=issues, bug_detected=len(issues) > 0, severity="MEDIUM", bug_type="CSS Syntax Issue")

def run_static_analysis(code, language):
    if not code or not str(code).strip(): return create_analysis_result([])
    language = normalize_language(language)
    code = str(code)
    if language not in SUPPORTED_LANGUAGES:
        return create_analysis_result(issues=[f"Static analysis is not available for language '{language}'."], bug_detected=False, severity="NONE", bug_type=None)
    if language == "python": return run_python_static_analysis(code)
    if language == "javascript": return run_javascript_static_analysis(code)
    if language == "java": return run_java_static_analysis(code)
    if language in {"c", "c++"}: return run_c_cpp_static_analysis(code)
    if language == "html": return run_html_static_analysis(code)
    if language == "css": return run_css_static_analysis(code)
    return create_analysis_result([])