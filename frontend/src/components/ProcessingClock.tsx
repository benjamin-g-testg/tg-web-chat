import { useEffect, useState } from "react";

export default function ProcessingClock() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="processing-indicator">
      <span className="processing-spinner" />
      <span className="processing-text">
        Procesando consulta y análisis Jira
      </span>
      <span className="processing-time">({seconds}s)</span>
    </div>
  );
}
