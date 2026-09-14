import React, { useEffect, useState } from "react";
import {
  fetchGlobalArtifacts,
  type GlobalArtifactsResponse,
} from "../services/api";

interface ArtifactsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PHASE_LABELS: Record<string, string> = {
  phase_1: "Fase 1: Calidad de Datos",
  phase_2: "Fase 2: Hallazgos e Insights",
  phase_3: "Fase 3: Respuesta a Consulta",
  conclusion: "Conclusión y Recomendaciones",
  executive_summary: "Resumen Ejecutivo",
};

export default function ArtifactsModal({ isOpen, onClose }: ArtifactsModalProps) {
  const [data, setData] = useState<GlobalArtifactsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchGlobalArtifacts()
        .then((res) => setData(res))
        .catch((err) => console.error("Error al cargar artefactos:", err))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredInventory = (data?.inventory || []).filter((item) =>
    item.session_title.toLowerCase().includes(search.toLowerCase()) ||
    item.files.some((f) => f.filename.toLowerCase().includes(search.toLowerCase()))
  );

  const totalFiles = (data?.inventory || []).reduce((acc, curr) => acc + curr.files.length, 0);

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <div className="modal-title-group">
            <h3 id="modal-title" className="modal-title">Repositorio Central de Archivos y Reportes</h3>
            <span className="modal-subtitle">
              {totalFiles} archivos generados a través de {data?.total_jobs || 0} sesiones de análisis
            </span>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Cerrar modal">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>

        <div className="modal-search-bar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Buscar archivos por nombre de consulta o título de reporte..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="modal-content-scroll">
          {loading ? (
            <div className="modal-loading-state">
              <span className="processing-spinner" />
              <span>Cargando inventario de archivos...</span>
            </div>
          ) : filteredInventory.length > 0 ? (
            filteredInventory.map((item) => (
              <section key={item.job_id} className="artifact-session-group">
                <div className="session-group-header">
                  <div className="session-group-title">
                    <span className="session-indicator" />
                    <strong>{item.session_title}</strong>
                  </div>
                  <span className="session-group-date">
                    {new Date(item.created_at).toLocaleString("es-CL", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div className="artifact-files-grid">
                  {item.files.map((file) => {
                    const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
                    const downloadUrl = `${baseUrl.replace(/\/api$/, "")}${file.download_url}`;
                    const isWord = file.format === "word";

                    return (
                      <div key={`${file.filename}-${file.format}`} className="artifact-file-card">
                        <div className="file-card-info">
                          <span className={`file-badge ${isWord ? "word" : "pdf"}`}>
                            {isWord ? "DOCX" : "PDF"}
                          </span>
                          <div className="file-card-titles">
                            <span className="file-phase-name">{PHASE_LABELS[file.phase] || file.phase}</span>
                            <span className="file-real-name">{file.filename}</span>
                          </div>
                        </div>
                        <a
                          href={downloadUrl}
                          download={isWord}
                          target={isWord ? undefined : "_blank"}
                          rel="noreferrer"
                          className={`file-download-btn ${isWord ? "word" : "pdf"}`}
                          title={`Descargar ${file.filename}`}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                          </svg>
                          Descargar
                        </a>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))
          ) : (
            <div className="modal-empty-state">
              <p>No se encontraron reportes generados con ese criterio.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
