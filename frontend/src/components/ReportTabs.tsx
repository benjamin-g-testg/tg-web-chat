import { useState } from "react";
import type { ReportData, ArtifactFiles } from "../services/api";
import { getArtifactUrl } from "../services/api";

const TAB_CONFIG: Array<{ key: keyof ReportData; badge: string; label: string }> = [
  { key: "phase_1", badge: "1", label: "Fase 1: Calidad" },
  { key: "phase_2", badge: "2", label: "Fase 2: Hallazgos" },
  { key: "phase_3", badge: "3", label: "Fase 3: Respuesta" },
  { key: "conclusion", badge: "C", label: "Conclusión" },
  { key: "executive_summary", badge: "RE", label: "Resumen Ejecutivo" },
];

interface ReportTabsProps {
  reports: ReportData;
  artifacts?: ArtifactFiles | null;
  jobId?: string;
}

export default function ReportTabs({ reports, artifacts, jobId }: ReportTabsProps) {
  const [activeTab, setActiveTab] = useState<keyof ReportData>("conclusion");
  const currentTab = TAB_CONFIG.find((tab) => tab.key === activeTab) || TAB_CONFIG[0];

  const wordFilename = artifacts?.word?.[activeTab];
  const pdfFilename = artifacts?.pdf?.[activeTab];

  const wordUrl = wordFilename && jobId ? getArtifactUrl("word", wordFilename, jobId) : null;
  const pdfUrl = pdfFilename && jobId ? getArtifactUrl("pdf", pdfFilename, jobId) : null;

  return (
    <section className="report-panel" aria-label="Reportes detallados del análisis QA">
      <div className="report-tabs-header" role="tablist">
        {TAB_CONFIG.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            className={`tab-button ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            <span className="tab-badge">{tab.badge}</span>
            <span className="tab-text">{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="report-content-body">
        <h4 className="report-section-title">{currentTab.label}</h4>
        <div className="report-text-container">
          {reports[activeTab] ? (
            <p className="report-paragraph">{reports[activeTab]}</p>
          ) : (
            <p className="report-empty">No hay información registrada para esta fase.</p>
          )}
        </div>

        <div className="report-downloads-section">
          <span className="downloads-label">Descargar reporte oficial en formato:</span>
          <div className="downloads-buttons-group">
            {wordUrl ? (
              <a
                href={wordUrl}
                download
                className="format-btn word-btn"
                title={`Descargar ${currentTab.label} en formato Word (.docx)`}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                <span>Word (.docx)</span>
              </a>
            ) : (
              <span className="format-btn-disabled">Word disponible al generar</span>
            )}

            {pdfUrl ? (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className="format-btn pdf-btn"
                title={`Visualizar o descargar ${currentTab.label} en formato PDF`}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
                <span>PDF (.pdf)</span>
              </a>
            ) : (
              <span className="format-btn-disabled">PDF disponible al generar</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
