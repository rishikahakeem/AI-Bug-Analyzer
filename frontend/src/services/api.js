
import axios from "axios";

// =========================================================
// AXIOS API INSTANCE
// =========================================================

const API = axios.create({
  baseURL: "https://ai-bug-analyzer-p2wc.onrender.com",
  headers: {
    "Content-Type": "application/json",
  },
});

// =========================================================
// ANALYZE CODE
// =========================================================

export const analyzeCode = async (
  code,
  language
) => {
  const userId =
    localStorage.getItem("userId");

  const response =
    await API.post(
      "/api/analyze",
      {
        code,
        language,
        user_id: userId,
      }
    );

  return response.data;
};

// =========================================================
// GET ANALYSIS HISTORY
// =========================================================

export const getAnalysisHistory = async () => {
  const userId =
    localStorage.getItem("userId");

  if (!userId) {
    throw new Error(
      "User ID not found. Please login again."
    );
  }

  const response =
    await API.get(
      `/api/history/${userId}`
    );

  return response.data;
};

// =========================================================
// DELETE ANALYSIS HISTORY
// =========================================================

export const deleteAnalysis =
  async (analysisId) => {
    const response =
      await API.delete(
        `/api/history/${analysisId}`
      );

    return response.data;
  };

// =========================================================
// GET GITHUB REPOSITORY FILES
// =========================================================

export const getGithubFiles =
  async (githubUrl) => {
    const response =
      await API.post(
        "/api/github/files",
        {
          url: githubUrl,
        }
      );

    return response.data;
  };

// =========================================================
// GET GITHUB FILE CONTENT
// =========================================================

export const getGithubFile =
  async (
    owner,
    repo,
    path
  ) => {
    const response =
      await API.post(
        "/api/github/file",
        {
          owner,
          repo,
          path,
        }
      );

    return response.data;
  };

// =========================================================
// EXPORT API INSTANCE
// =========================================================

export default API;
