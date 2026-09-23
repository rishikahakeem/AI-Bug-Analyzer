import {
  FaBug,
  FaRobot,
  FaCode,
  FaHistory,
  FaShieldAlt,
  FaLightbulb,
  FaBolt,
  FaDatabase,
} from "react-icons/fa";

function Features() {

  const features = [
    {
      icon: <FaBug />,
      title: "Intelligent Bug Detection",
      text: "Detect syntax, logical and runtime problems in your source code."
    },
    {
      icon: <FaRobot />,
      title: "AI-Powered Analysis",
      text: "Use Llama 3.2 to understand your code and identify potential issues."
    },
    {
      icon: <FaCode />,
      title: "Code Fix Suggestions",
      text: "Get practical corrections and improved versions of your code."
    },
    {
      icon: <FaHistory />,
      title: "Analysis History",
      text: "Keep track of previous analyses and revisit important debugging sessions."
    },
    {
      icon: <FaShieldAlt />,
      title: "Local AI Processing",
      text: "Use Ollama locally without depending on paid AI APIs."
    },
    {
      icon: <FaLightbulb />,
      title: "Beginner-Friendly Explanations",
      text: "Understand complex programming errors through simple explanations."
    },
    {
      icon: <FaBolt />,
      title: "Fast Analysis",
      text: "Send your code directly to the backend for AI-powered analysis."
    },
    {
      icon: <FaDatabase />,
      title: "Persistent Data",
      text: "Store user accounts and analysis history using MySQL."
    }
  ];

  return (
    <main className="features-page">

      <div className="page-header">

        <span>PLATFORM FEATURES</span>

        <h1>
          Everything you need
          <br />
          to debug better.
        </h1>

        <p>
          A complete AI-powered toolkit designed
          to help developers understand and fix code.
        </p>

      </div>


      <div className="features-grid">

        {features.map((feature, index) => (

          <div className="feature-card" key={index}>

            <div className="feature-icon">
              {feature.icon}
            </div>

            <span className="feature-number">
              0{index + 1}
            </span>

            <h3>{feature.title}</h3>

            <p>{feature.text}</p>

          </div>

        ))}

      </div>

    </main>
  );
}

export default Features;