import os

from flask import Blueprint, request, jsonify
import requests
from urllib.parse import urlparse


github_bp = Blueprint("github", __name__)

GITHUB_API = "https://api.github.com"


ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".html",
    ".htm",
    ".css",
}


MAX_FILES = 50
MAX_FILE_SIZE = 200_000  # 200 KB


# ============================================================
# GITHUB URL PARSER
# ============================================================

def parse_github_url(github_url):
    """
    Extract owner and repository name from:

    https://github.com/owner/repository
    """

    try:
        parsed = urlparse(github_url)

        if parsed.netloc.lower() != "github.com":
            return None, None

        parts = [
            part
            for part in parsed.path.strip("/").split("/")
            if part
        ]

        if len(parts) < 2:
            return None, None

        owner = parts[0]
        repo = parts[1]

        if repo.endswith(".git"):
            repo = repo[:-4]

        return owner, repo

    except Exception:
        return None, None


# ============================================================
# GITHUB HEADERS
# ============================================================

def github_headers():
    """
    Build GitHub API request headers.

    GITHUB_TOKEN is read from the environment.
    On Render, this comes from the GITHUB_TOKEN
    environment variable.
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Bug-Analyzer",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    github_token = os.getenv("GITHUB_TOKEN")

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    return headers


# ============================================================
# LOAD REPOSITORY FILES
# ============================================================

@github_bp.route("/api/github/files", methods=["POST"])
def get_github_files():

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required."
            }), 400

        github_url = str(
            data.get("url", "")
        ).strip()

        if not github_url:
            return jsonify({
                "success": False,
                "message": "GitHub repository URL is required."
            }), 400

        owner, repo = parse_github_url(
            github_url
        )

        if not owner or not repo:
            return jsonify({
                "success": False,
                "message": "Please enter a valid GitHub repository URL."
            }), 400

        print(
            "GitHub owner:",
            owner
        )

        print(
            "GitHub repository:",
            repo
        )

        # ------------------------------------------------------
        # STEP 1: GET REPOSITORY INFORMATION
        # ------------------------------------------------------

        repo_url = (
            f"{GITHUB_API}/repos/"
            f"{owner}/{repo}"
        )

        repo_response = requests.get(
            repo_url,
            headers=github_headers(),
            timeout=15
        )

        print(
            "GitHub repository status:",
            repo_response.status_code
        )

        if repo_response.status_code == 404:
            return jsonify({
                "success": False,
                "message": (
                    "GitHub repository not found. "
                    "Make sure the repository is public "
                    "and the URL is correct."
                )
            }), 404

        if repo_response.status_code == 403:
            print(
                "GitHub 403 response:",
                repo_response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "GitHub denied the request (403). "
                    "The GitHub token may be invalid, "
                    "expired, or rate-limited."
                )
            }), 403

        if not repo_response.ok:
            print(
                "GitHub repository error:",
                repo_response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    f"GitHub repository request failed "
                    f"with status {repo_response.status_code}."
                )
            }), 500

        repository_data = repo_response.json()

        default_branch = (
            repository_data.get(
                "default_branch",
                "main"
            )
        )

        # ------------------------------------------------------
        # STEP 2: GET REPOSITORY TREE
        # ------------------------------------------------------

        tree_url = (
            f"{GITHUB_API}/repos/"
            f"{owner}/{repo}/git/trees/"
            f"{default_branch}?recursive=1"
        )

        tree_response = requests.get(
            tree_url,
            headers=github_headers(),
            timeout=20
        )

        print(
            "GitHub tree status:",
            tree_response.status_code
        )

        if tree_response.status_code == 403:
            print(
                "GitHub tree 403 response:",
                tree_response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "GitHub denied access while reading "
                    "the repository files."
                )
            }), 403

        if not tree_response.ok:
            print(
                "GitHub tree error:",
                tree_response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "Could not read files from the "
                    "GitHub repository."
                )
            }), 500

        tree_data = tree_response.json()

        tree = tree_data.get(
            "tree",
            []
        )

        if tree_data.get("truncated"):
            print(
                "GitHub tree was truncated."
            )

        files = []

        # ------------------------------------------------------
        # STEP 3: FILTER SUPPORTED SOURCE FILES
        # ------------------------------------------------------

        for item in tree:

            if item.get("type") != "blob":
                continue

            path = item.get(
                "path",
                ""
            )

            size = item.get(
                "size",
                0
            ) or 0

            lower_path = path.lower()

            supported = False

            for extension in ALLOWED_EXTENSIONS:

                if lower_path.endswith(
                    extension
                ):
                    supported = True
                    break

            if not supported:
                continue

            if size > MAX_FILE_SIZE:
                continue

            files.append({
                "path": path,
                "size": size,
                "sha": item.get("sha"),
            })

            if len(files) >= MAX_FILES:
                break

        # ------------------------------------------------------
        # STEP 4: RETURN FILE LIST
        # ------------------------------------------------------

        return jsonify({
            "success": True,
            "message": (
                "GitHub repository loaded successfully."
            ),
            "repository": f"{owner}/{repo}",
            "branch": default_branch,
            "files": files,
            "file_count": len(files)
        }), 200

    except requests.exceptions.Timeout:

        return jsonify({
            "success": False,
            "message": (
                "GitHub request timed out. "
                "Please try again."
            )
        }), 504

    except requests.exceptions.RequestException as error:

        print(
            "GitHub request error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not connect to GitHub."
            )
        }), 500

    except Exception as error:

        print(
            "GitHub integration error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                f"GitHub integration failed: {error}"
            )
        }), 500


# ============================================================
# LOAD SELECTED GITHUB FILE
# ============================================================

@github_bp.route("/api/github/file", methods=["POST"])
def get_github_file():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required."
            }), 400

        owner = str(
            data.get("owner", "")
        ).strip()

        repo = str(
            data.get("repo", "")
        ).strip()

        path = str(
            data.get("path", "")
        ).strip()

        if not owner or not repo or not path:
            return jsonify({
                "success": False,
                "message": (
                    "Owner, repository and "
                    "file path are required."
                )
            }), 400

        # ------------------------------------------------------
        # FETCH SELECTED FILE
        # ------------------------------------------------------

        file_url = (
            f"{GITHUB_API}/repos/"
            f"{owner}/{repo}/contents/"
            f"{path}"
        )

        headers = github_headers()

        headers["Accept"] = (
            "application/vnd.github.raw+json"
        )

        response = requests.get(
            file_url,
            headers=headers,
            timeout=20
        )

        print(
            "GitHub file status:",
            response.status_code
        )

        if response.status_code == 404:
            return jsonify({
                "success": False,
                "message": (
                    "File not found in the "
                    "GitHub repository."
                )
            }), 404

        if response.status_code == 403:
            print(
                "GitHub file 403 response:",
                response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "GitHub denied access while "
                    "downloading this file."
                )
            }), 403

        if not response.ok:
            print(
                "GitHub file error:",
                response.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "Could not download the "
                    "selected GitHub file."
                )
            }), 500

        code = response.text

        if len(code) > MAX_FILE_SIZE:
            return jsonify({
                "success": False,
                "message": (
                    "Selected file is too large. "
                    "Please choose a file below "
                    "200 KB."
                )
            }), 413

        return jsonify({
            "success": True,
            "message": (
                "GitHub file loaded successfully."
            ),
            "path": path,
            "code": code
        }), 200

    except requests.exceptions.Timeout:

        return jsonify({
            "success": False,
            "message": (
                "GitHub file request timed out."
            )
        }), 504

    except requests.exceptions.RequestException as error:

        print(
            "GitHub file request error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not connect to GitHub."
            )
        }), 500

    except Exception as error:

        print(
            "GitHub file error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                f"Could not load GitHub file: {error}"
            )
        }), 500