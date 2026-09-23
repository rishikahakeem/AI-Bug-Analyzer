import { Link } from "react-router-dom";

import {
  FaBug,
  FaRobot,
  FaCode,
  FaShieldAlt,
  FaBolt,
  FaArrowRight,
  FaCheckCircle,
} from "react-icons/fa";

function Home() {
  return (
    <main className="home-page">

      {/* HERO */}

      <section className="hero">
        <div className="hero-badge">
          <FaRobot />
          Powered by AI + Llama 3.2
        </div>

        <h1>
          Debug smarter.
          <br />
          <span>Build better.</span>
        </h1>

        <p className="hero-description">
          AI-powered code analysis that detects bugs, explains
          complex errors, and helps developers fix problems faster.
        </p>

        <div className="hero-buttons">
          <Link to="/analyzer" className="primary-button">
            Analyze Your Code
            <FaArrowRight />
          </Link>

          <Link to="/features" className="secondary-button">
            Explore Features
          </Link>
        </div>

        <div className="hero-trust">
          <div>
            <FaCheckCircle />
            AI-powered analysis
          </div>

          <div>
            <FaCheckCircle />
            Multiple languages
          </div>

          <div>
            <FaCheckCircle />
            Local AI processing
          </div>
        </div>
      </section>


      {/* STATS */}

      <section className="stats-section">

        <div className="stat-card">
          <strong>6+</strong>
          <span>Languages</span>
        </div>

        <div className="stat-card">
          <strong>AI</strong>
          <span>Powered Analysis</span>
        </div>

        <div className="stat-card">
          <strong>24/7</strong>
          <span>Available</span>
        </div>

        <div className="stat-card">
          <strong>100%</strong>
          <span>Developer Focused</span>
        </div>

      </section>


      {/* FEATURES */}

      <section className="home-section">

        <div className="section-heading">
          <span>WHY BUGAI</span>

          <h2>
            Your intelligent
            <br />
            debugging assistant
          </h2>

          <p>
            Stop spending hours searching for bugs.
            Let AI understand your code and guide you
            towards a solution.
          </p>
        </div>


        <div className="home-feature-grid">

          <div className="large-feature-card">

            <div className="feature-number">
              01
            </div>

            <div className="large-feature-icon">
              <FaBug />
            </div>

            <h3>Detect Bugs</h3>

            <p>
              Identify syntax errors, logical problems,
              runtime issues and potential bugs in your code.
            </p>

            <Link to="/analyzer">
              Analyze Code <FaArrowRight />
            </Link>

          </div>


          <div className="large-feature-card">

            <div className="feature-number">
              02
            </div>

            <div className="large-feature-icon">
              <FaRobot />
            </div>

            <h3>Understand Errors</h3>

            <p>
              Get clear explanations of what went wrong,
              why it happened and how to prevent it.
            </p>

            <Link to="/analyzer">
              Ask AI <FaArrowRight />
            </Link>

          </div>


          <div className="large-feature-card">

            <div className="feature-number">
              03
            </div>

            <div className="large-feature-icon">
              <FaCode />
            </div>

            <h3>Fix Your Code</h3>

            <p>
              Receive corrected code and practical
              suggestions you can apply immediately.
            </p>

            <Link to="/analyzer">
              Fix Bugs <FaArrowRight />
            </Link>

          </div>

        </div>

      </section>


      {/* HOW IT WORKS */}

      <section className="how-section">

        <div className="section-heading">
          <span>HOW IT WORKS</span>

          <h2>
            From bug to solution
            <br />
            in three steps.
          </h2>
        </div>


        <div className="steps-grid">

          <div className="step-card">
            <div className="step-icon">
              <FaCode />
            </div>

            <span>01</span>

            <h3>Paste Your Code</h3>

            <p>
              Select your programming language
              and paste your code into the analyzer.
            </p>
          </div>


          <div className="step-card">
            <div className="step-icon">
              <FaBolt />
            </div>

            <span>02</span>

            <h3>AI Analyzes</h3>

            <p>
              Llama 3.2 analyzes your code and
              identifies potential problems.
            </p>
          </div>


          <div className="step-card">
            <div className="step-icon">
              <FaShieldAlt />
            </div>

            <span>03</span>

            <h3>Get Your Solution</h3>

            <p>
              Receive an explanation, suggested fix
              and corrected code.
            </p>
          </div>

        </div>

      </section>


      {/* CTA */}

      <section className="home-cta">

        <div>
          <span>READY TO DEBUG?</span>

          <h2>
            Find the bug.
            <br />
            Fix the code.
          </h2>

          <p>
            Start analyzing your code with AI today.
          </p>
        </div>

        <Link to="/analyzer" className="cta-button">
          Open Analyzer
          <FaArrowRight />
        </Link>

      </section>

    </main>
  );
}

export default Home;