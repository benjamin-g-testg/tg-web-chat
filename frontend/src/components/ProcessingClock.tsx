import { useEffect, useState } from "react";
export default function ProcessingClock() { const [seconds, setSeconds] = useState(0); useEffect(() => { const id = setInterval(() => setSeconds((v) => v + 1), 1000); return () => clearInterval(id); }, []); return <div className="processing"><span className="spinner" />Analizando pipeline Jira · {seconds}s</div>; }
