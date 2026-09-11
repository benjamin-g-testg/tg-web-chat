import { useState } from "react";
import type { Reports } from "../services/api";
const tabs: Array<[keyof Reports, string, string]> = [["phase_1", "1", "Fase 1"], ["phase_2", "2", "Fase 2"], ["phase_3", "3", "Fase 3"], ["conclusion", "C", "Conclusión"], ["executive_summary", "RE", "Resumen ejecutivo"]];
export default function ReportTabs({ reports }: { reports: Reports }) { const [active, setActive] = useState<keyof Reports>("conclusion"); const current = tabs.find(([key]) => key === active)!; return <section className="report"><div className="tabs">{tabs.map(([key, label, title]) => <button key={key} className={active === key ? "active" : ""} title={title} onClick={() => setActive(key)}>{label}</button>)}</div><h3>{current[2]}</h3><p>{reports[active]}</p></section>; }
