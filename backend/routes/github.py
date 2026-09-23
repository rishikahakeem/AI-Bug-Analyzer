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


def github_headers():
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Bug-Analyzer",
    }


@github_bp.route("/api/github/files", methods=["POST"])
def get_github_files():

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required."
            }), 400

        github_url = str(data.get("url", "")).strip()

        if not github_url:
            return jsonify({
                "success": False,
                "message": "GitHub repository URL is required."
            }), 400

        owner, repo = parse_github_url(github_url)

        if not owner or not repo:
            return jsonify({
                "success": False,
                "message": "Please enter a valid GitHub repository URL."
            }), 400

        print("GitHub owner:", owner)
        print("GitHub repository:", repo)

        # -------------------------------------------------------
        # STEP 1: Get repository information
        # -------------------------------------------------------

        repo_url = f"{GITHUB_API}/repos/{owner}/{repo}"

        repo_response = requests.get(
            repo_url,
            headers=github_headers(),
            timeout=15
        )

        if repo_response.status_code == 404:
            return jsonify({
                "success": False,
                "message": "GitHub repository not found. Make sure it is public and the URL is correct."
            }), 404

        if not repo_response.ok:
            return jsonify({
                "success": False,
                "message": f"GitHub repository request failed with status {repo_response.status_code}."
            }), 500

        repository_data = repo_response.json()

        default_branch = repository_data.get(
            "default_branch",
            "main"
        )

        # -------------------------------------------------------
        # STEP 2: Get repository tree
        # -------------------------------------------------------

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

        if not tree_response.ok:
            return jsonify({
                "success": False,
                "message": "Could not read files from the GitHub repository."
            }), 500

        tree_data = tree_response.json()

        tree = tree_data.get("tree", [])

        if tree_data.get("truncated"):
            print("GitHub tree was truncated.")

        files = []

        # -------------------------------------------------------
        # STEP 3: Filter supported source files
        # -------------------------------------------------------

        for item in tree:

            if item.get("type") != "blob":
                continue

            path = item.get("path", "")
            size = item.get("size", 0) or 0

            lower_path = path.lower()

            supported = False

            for extension in ALLOWED_EXTENSIONS:
                if lower_path.endswith(extension):
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

        # -------------------------------------------------------
        # STEP 4: Return repository file list
        # -------------------------------------------------------

        return jsonify({
            "success": True,
            "message": "GitHub repository loaded successfully.",
            "repository": f"{owner}/{repo}",
            "branch": default_branch,
            "files": files,
            "file_count": len(files)
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "GitHub request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as error:
        print("GitHub request error:", error)

        return jsonify({
            "success": False,
            "message": "Could not connect to GitHub."
        }), 500

    except Exception as error:
        print("GitHub integration error:", error)

        return jsonify({
            "success": False,
            "message": f"GitHub integration failed: {error}"
        }), 500


@github_bp.route("/api/github/file", methods=["POST"])
def get_github_file():

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required."
            }), 400

        owner = str(data.get("owner", "")).strip()
        repo = str(data.get("repo", "")).strip()
        path = str(data.get("path", "")).strip()

        if not owner or not repo or not path:
            return jsonify({
                "success": False,
                "message": "Owner, repository and file path are required."
            }), 400

        # -------------------------------------------------------
        # Fetch selected file
        # -------------------------------------------------------

        file_url = (
            f"{GITHUB_API}/repos/"
            f"{owner}/{repo}/contents/"
            f"{path}"
        )

        response = requests.get(
            file_url,
            headers={
                **github_headers(),
                "Accept": "application/vnd.github.raw+json",
            },
            timeout=20
        )

        if response.status_code == 404:
            return jsonify({
                "success": False,
                "message": "File not found in the GitHub repository."
            }), 404

        if not response.ok:
            return jsonify({
                "success": False,
                "message": "Could not download the selected GitHub file."
            }), 500

        code = response.text

        if len(code) > MAX_FILE_SIZE:
            return jsonify({
                "success": False,
                "message": "Selected file is too large. Please choose a file below 200 KB."
            }), 413

        return jsonify({
            "success": True,
            "message": "GitHub file loaded successfully.",
            "path": path,
            "code": code
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "GitHub file request timed out."
        }), 504

    except requests.exceptions.RequestException as error:
        print("GitHub file request error:", error)

        return jsonify({
            "success": False,
            "message": "Could not connect to GitHub."
        }), 500

    except Exception as error:
        print("GitHub file error:", error)

        return jsonify({
            "success": False,
            "message": f"Could not load GitHub file: {error}"
        }), 500