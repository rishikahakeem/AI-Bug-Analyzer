
import {
  FaBug,
  FaGithub,
  FaHeart,
} from "react-icons/fa";

function Footer() {

  return (
    <footer className="footer">

      <div className="footer-main">

        <div className="footer-brand">

          <div className="footer-logo">
            <FaBug />
            <strong>Bug<span>AI</span></strong>
          </div>

          <p>
            AI-powered code intelligence for
            developers who want to build better software.
          </p>

        </div>


        <div className="footer-column">

          <h4>Platform</h4>

          <a href="/">Home</a>
          <a href="/analyzer">Analyzer</a>
          <a href="/features">Features</a>
          <a href="/history">History</a>

        </div>


        <div className="footer-column">

          <h4>Technology</h4>

          <span>React.js</span>
          <span>Flask</span>
          <span>Ollama</span>
          <span>Llama 3.2</span>

        </div>


        <div className="footer-column">

          <h4>Developer</h4>

          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
          >
            <FaGithub /> GitHub
          </a>

        </div>

      </div>


      <div className="footer-bottom">

        <span>
          © 2026 BugAI. All rights reserved.
        </span>

        <span>
          Built with <FaHeart /> for developers.
        </span>

      </div>

    </footer>
  );
}

export default Footer;
