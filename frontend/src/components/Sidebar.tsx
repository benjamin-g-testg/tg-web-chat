import { useState, useMemo } from "react";
import type { SessionListItem } from "../services/api";
import ConfirmModal from "./ConfirmModal";

interface SidebarProps {
  history: SessionListItem[];
  currentSessionId?: string;
  onDownload: () => void;
  onOpenArtifacts: () => void;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
}

type SortOrder = "desc" | "asc";

export default function Sidebar({
  history,
  currentSessionId,
  onDownload,
  onOpenArtifacts,
  onSelect,
  onNewSession,
  onRenameSession,
  onDeleteSession,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  const sortedHistory = useMemo(() => {
    return [...history].sort((a, b) => {
      const dateA = new Date(a.updated_at || a.created_at || 0).getTime();
      const dateB = new Date(b.updated_at || b.created_at || 0).getTime();
      return sortOrder === "desc" ? dateB - dateA : dateA - dateB;
    });
  }, [history, sortOrder]);

  const startRename = (item: SessionListItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(item.id);
    setEditTitle(item.title);
  };

  const saveRename = (id: string, e: React.FormEvent | React.FocusEvent) => {
    e.preventDefault();
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const requestDelete = (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteTarget({ id, title });
  };

  const confirmDelete = () => {
    if (deleteTarget) {
      onDeleteSession(deleteTarget.id);
      setDeleteTarget(null);
    }
  };

  const cancelDelete = () => setDeleteTarget(null);

  const toggleSort = () =>
    setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));

  return (
    <>
      <aside className="sidebar-container" aria-label="Navegación lateral">
        <div className="brand-header">
          <div className="brand-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="brand-text">
            <span className="brand-title">Jira QA Assistant</span>
            <span className="brand-subtitle">Análisis Inteligente de Calidad</span>
          </div>
        </div>

        <button
          type="button"
          className="new-session-button"
          onClick={onNewSession}
          title="Iniciar una nueva conversación"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Nueva Consulta
        </button>

        <div className="history-section">
          <div className="history-header-row">
            <span className="history-header">HISTORIAL DE CONVERSACIONES</span>
            <button
              type="button"
              className="sort-toggle-btn"
              onClick={toggleSort}
              title={sortOrder === "desc" ? "Mostrando más recientes primero" : "Mostrando más antiguas primero"}
              aria-label={`Ordenar por fecha ${sortOrder === "desc" ? "ascendente" : "descendente"}`}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                {sortOrder === "desc" ? (
                  <>
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <polyline points="19 12 12 19 5 12" />
                  </>
                ) : (
                  <>
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </>
                )}
              </svg>
              {sortOrder === "desc" ? "Recientes" : "Antiguas"}
            </button>
          </div>

          <div className="history-list" role="list">
            {sortedHistory.length > 0 ? (
              sortedHistory.map((item) => {
                const isEditing = editingId === item.id;
                const dateStr = item.updated_at || item.created_at;
                const formattedDate = dateStr
                  ? new Date(dateStr).toLocaleString("es-CL", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "";

                return (
                  <div
                    key={item.id}
                    role="listitem"
                    className={`history-item-wrapper ${currentSessionId === item.id ? "active" : ""}`}
                    onClick={() => !isEditing && onSelect(item.id)}
                  >
                    {isEditing ? (
                      <form
                        className="history-edit-form"
                        onSubmit={(e) => saveRename(item.id, e)}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          autoFocus
                          onBlur={(e) => saveRename(item.id, e)}
                          maxLength={160}
                          aria-label="Nuevo nombre para la conversación"
                        />
                      </form>
                    ) : (
                      <>
                        <div className="history-item-content">
                          <div className="history-item-title" title={item.title}>
                            {item.title || "Consulta sin título"}
                          </div>
                          {formattedDate && (
                            <div className="history-item-date">{formattedDate}</div>
                          )}
                          {typeof item.message_count === "number" && (
                            <div className="history-item-count">
                              {item.message_count} {item.message_count === 1 ? "mensaje" : "mensajes"}
                            </div>
                          )}
                        </div>
                        <div className="history-item-actions" aria-label="Acciones de conversación">
                          <button
                            type="button"
                            className="history-action-btn edit"
                            onClick={(e) => startRename(item, e)}
                            title="Renombrar conversación"
                            aria-label="Renombrar conversación"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            className="history-action-btn delete"
                            onClick={(e) => requestDelete(item.id, item.title, e)}
                            title="Eliminar conversación"
                            aria-label="Eliminar conversación"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="history-empty">Las consultas anteriores aparecerán aquí.</div>
            )}
          </div>
        </div>

        <div className="sidebar-footer">
          <button
            type="button"
            className="artifacts-explorer-button"
            onClick={onOpenArtifacts}
            title="Ver todos los archivos y reportes Word y PDF generados"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            Explorador de Archivos
          </button>

          <button
            type="button"
            className="download-excel-button"
            onClick={onDownload}
            title="Descargar resumen de la sesión actual en formato Excel"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Exportar Resumen Excel
          </button>
        </div>
      </aside>

      <ConfirmModal
        isOpen={deleteTarget !== null}
        title="Eliminar conversación"
        message={`¿Confirmas que deseas eliminar "${deleteTarget?.title ?? ""}"? Esta acción no puede deshacerse.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </>
  );
}
