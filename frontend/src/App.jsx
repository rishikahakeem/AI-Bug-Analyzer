import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router";

import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

import Home from "./pages/Home";
import Analyzer from "./pages/Analyzer";
import Features from "./pages/Features";
import History from "./pages/HistoryPage";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Admin from "./pages/Admin";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

import "./App.css";


/* ============================================================
   LOGIN CHECK
   ============================================================ */

const isLoggedIn = () => {
  return Boolean(
    localStorage.getItem("userId")
  );
};


/* ============================================================
   PROTECTED ROUTE
   Login required
   ============================================================ */

const ProtectedRoute = ({ children }) => {
  if (!isLoggedIn()) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
};


/* ============================================================
   PUBLIC-ONLY ROUTE
   Login / Signup / Password pages
   ============================================================ */

const PublicOnlyRoute = ({ children }) => {
  if (isLoggedIn()) {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
  }

  return children;
};


/* ============================================================
   APP
   ============================================================ */

function App() {
  return (
    <BrowserRouter>

      {/* Navbar is always visible */}
      <Navbar />

      <Routes>

        {/* ==================================================
            HOME
            Everyone can access
            ================================================== */}

        <Route
          path="/"
          element={<Home />}
        />


        {/* ==================================================
            FEATURES
            Everyone can access
            ================================================== */}

        <Route
          path="/features"
          element={<Features />}
        />


        {/* ==================================================
            ANALYZER
            Login required
            ================================================== */}

        <Route
          path="/analyzer"
          element={
            <ProtectedRoute>
              <Analyzer />
            </ProtectedRoute>
          }
        />


        {/* ==================================================
            HISTORY
            Login required
            ================================================== */}

        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <History />
            </ProtectedRoute>
          }
        />


        {/* ==================================================
            DASHBOARD
            Login required
            ================================================== */}

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />


        {/* ==================================================
            PROFILE
            Login required
            Normal user + Admin
            ================================================== */}

        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />


        {/* ==================================================
            ADMIN
            Login required
            Admin.jsx checks admin permission
            ================================================== */}

        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <Admin />
            </ProtectedRoute>
          }
        />


        {/* ==================================================
            LOGIN
            Logged-out users only
            ================================================== */}

        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          }
        />


        {/* ==================================================
            SIGNUP
            ================================================== */}

        <Route
          path="/signup"
          element={
            <PublicOnlyRoute>
              <Signup />
            </PublicOnlyRoute>
          }
        />


        {/* ==================================================
            FORGOT PASSWORD
            ================================================== */}

        <Route
          path="/forgot-password"
          element={
            <PublicOnlyRoute>
              <ForgotPassword />
            </PublicOnlyRoute>
          }
        />


        {/* ==================================================
            RESET PASSWORD
            ================================================== */}

        <Route
          path="/reset-password"
          element={
            <PublicOnlyRoute>
              <ResetPassword />
            </PublicOnlyRoute>
          }
        />


        {/* ==================================================
            UNKNOWN URL
            ================================================== */}

        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />

      </Routes>

      <Footer />

    </BrowserRouter>
  );
}

export default App;