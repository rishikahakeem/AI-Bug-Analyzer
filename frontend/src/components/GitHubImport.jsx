import { useState } from "react";
import { FaGithub, FaFolderOpen, FaFileCode } from "react-icons/fa";

import {
  getGithubFiles,
  getGithubFile,
} from "../services/api";

import "./GitHubImport.css";


function getLanguageFromFileName(fileName) {

  const extension = fileName
    .split(".")
    .pop()
    .toLowerCase();

  switch (extension) {

    case "py":
      return "Python";

    case "js":
    case "jsx":
      return "JavaScript";

    case "java":
      return "Java";

    case "c":
    case "h":
      return "C";

    case "cpp":
    case "hpp":
      return "C++";

    case "html":
    case "htm":
      return "HTML";

    case "css":
      return "CSS";

    default:
      return "Python";
  }
}


function GitHubImport({ onCodeLoaded }) {

  const [githubUrl, setGithubUrl] = useState("");
  const [files, setFiles] = useState([]);
  const [repository, setRepository] = useState("");
  const [branch, setBranch] = useState("");

  const [loading, setLoading] = useState(false);
  const [fileLoading, setFileLoading] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleLoadRepository = async () => {

    setError("");
    setMessage("");
    setFiles([]);

    if (!githubUrl.trim()) {

      setError("Please enter a GitHub repository URL.");

      return;
    }

    setLoading(true);

    try {

      const data = await getGithubFiles(githubUrl.trim());

      if (!data.success) {

        setError(
          data.message || "Could not load GitHub repository."
        );

        return;
      }

      setRepository(data.repository || "");
      setBranch(data.branch || "");
      setFiles(data.files || []);

      if (!data.files || data.files.length === 0) {

        setMessage(
          "No supported source files were found in this repository."
        );

      } else {

        setMessage(
          `${data.files.length} supported file(s) found. Select a file below.`
        );
      }

    } catch (err) {

      console.error("GitHub repository error:", err);

      setError(
        err.response?.data?.message ||
        "Could not connect to the GitHub repository."
      );

    } finally {

      setLoading(false);
    }
  };


  const handleLoadFile = async (file) => {

    setError("");
    setMessage("");
    setFileLoading(true);

    try {

      const [owner, repo] = repository.split("/");

      if (!owner || !repo) {

        setError("Repository information is missing.");

        return;
      }

      const data = await getGithubFile(
        owner,
        repo,
        file.path
      );

      if (!data.success) {

        setError(
          data.message || "Could not load the selected file."
        );

        return;
      }

      const detectedLanguage =
        getLanguageFromFileName(file.path);

      const fileName = file.path.split("/").pop();

      onCodeLoaded({
        code: data.code || "",
        language: detectedLanguage,
        fileName: fileName,
      });

      setMessage(
        `${fileName} loaded into the Analyzer.`
      );

    } catch (err) {

      console.error("GitHub file error:", err);

      setError(
        err.response?.data?.message ||
        "Could not load the selected GitHub file."
      );

    } finally {

      setFileLoading(false);
    }
  };


  return (
    <div className="github-import-card">

      <div className="github-import-header">

        <div className="github-import-title">

          <FaGithub />

          <div>
            <h3>Import from GitHub</h3>

            <p>
              Load source code from a public GitHub repository
              directly into the Analyzer.
            </p>
          </div>

        </div>

      </div>


      <div className="github-input-row">

        <input
          type="text"
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
          placeholder="https://github.com/username/repository"
          className="github-url-input"
        />

        <button
          type="button"
          className="github-load-button"
          onClick={handleLoadRepository}
          disabled={loading}
        >

          <FaFolderOpen />

          {loading
            ? "Loading..."
            : "Load Repository"}

        </button>

      </div>


      {repository && (
        <div className="github-repository-info">

          <strong>
            Repository:
          </strong>

          <span>
            {repository}
          </span>

          {branch && (
            <>
              <strong>
                Branch:
              </strong>

              <span>
                {branch}
              </span>
            </>
          )}

        </div>
      )}


      {message && (
        <div className="github-success-message">
          {message}
        </div>
      )}


      {error && (
        <div className="github-error-message">
          {error}
        </div>
      )}


      {files.length > 0 && (
        <div className="github-file-list">

          <div className="github-file-list-title">

            <FaFileCode />

            <span>
              Available Source Files
            </span>

          </div>


          <div className="github-files">

            {files.map((file) => (

              <div
                className="github-file-item"
                key={file.path}
              >

                <div className="github-file-name">

                  <FaFileCode />

                  <span>
                    {file.path}
                  </span>

                </div>


                <button
                  type="button"
                  className="github-select-button"
                  onClick={() => handleLoadFile(file)}
                  disabled={fileLoading}
                >

                  {fileLoading
                    ? "Loading..."
                    : "Load"}

                </button>

              </div>

            ))}

          </div>

        </div>
      )}

    </div>
  );
}

export default GitHubImport;