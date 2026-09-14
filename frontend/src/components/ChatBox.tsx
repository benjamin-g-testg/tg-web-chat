import { useState, useRef, useEffect } from "react";
import ProcessingClock from "./ProcessingClock";
import ReportTabs from "./ReportTabs";
import MetricsCards from "./MetricsCards";
import type { ChatMessageItem } from "../services/api";

interface ChatBoxProps {
  messages: ChatMessageItem[];
  loading: boolean;
  onSend: (message: string) => void;
}

export default function ChatBox({ messages, loading, onSend }: ChatBoxProps) {
  const [text, setText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = () => {
    if (text.trim() && !loading) {
      onSend(text.trim());
      setText("");
    }
  };

  return (
    <main className="chat-main-container" aria-label="Área de conversación">
      <header className="chat-header">
        <div className="header-status-indicator" aria-hidden="true" />
        <div className="header-info">
          <h2 className="header-title">Analista QA Jira</h2>
          <span className="header-version">Pipeline & Orquestación v2.4</span>
        </div>
      </header>

      <div className="chat-messages-scroll" role="log" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-welcome-banner">
            <div className="welcome-icon" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h1 className="welcome-heading">¿Qué deseas analizar hoy?</h1>
            <p className="welcome-description">
              Pregunta directamente sobre incidencias, estado de defectos, métricas por responsable o solicita reportes ejecutivos completos.
            </p>
            <div className="welcome-quick-queries">
              <button
                type="button"
                className="quick-query-pill"
                onClick={() => onSend("¿Cuáles son las incidencias bloqueadas?")}
              >
                ¿Cuáles son las incidencias bloqueadas?
              </button>
              <button
                type="button"
                className="quick-query-pill"
                onClick={() => onSend("¿De qué tratan los issues completados?")}
              >
                ¿De qué tratan los issues completados?
              </button>
              <button
                type="button"
                className="quick-query-pill"
                onClick={() => onSend("¿Qué incidencias están en progreso?")}
              >
                ¿Qué incidencias están en progreso?
              </button>
              <button
                type="button"
                className="quick-query-pill"
                onClick={() => onSend("Generar reporte ejecutivo del sprint actual")}
              >
                Reporte ejecutivo general
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => {
            const timeFormatted = message.timestamp
              ? new Date(message.timestamp).toLocaleTimeString("es-CL", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
              : "";

            return (
              <article key={message.id} className={`chat-message-row ${message.role}`}>
                <div className="message-avatar" aria-hidden="true">
                  {message.role === "user" ? "U" : "QA"}
                </div>
                <div className="message-content-wrapper">
                  <div className="message-meta-header">
                    <span className="message-author-label">
                      {message.role === "user" ? "Usuario" : "Asistente QA"}
                    </span>
                    {timeFormatted && (
                      <span className="message-time-label">{timeFormatted}</span>
                    )}
                  </div>

                  {message.agent && message.agent.intent && message.agent.intent !== "general_query" && (
                    <div className="agent-intent-badge">
                      <span className="badge-label">Intención:</span>
                      <span className="badge-value">{message.agent.intent.replace(/_/g, " ")}</span>
                    </div>
                  )}

                  <div className="message-bubble">
                    <div className="bubble-text">{message.content}</div>
                  </div>

                  {message.metrics && <MetricsCards metrics={message.metrics} />}

                  {message.reports && (
                    <ReportTabs
                      reports={message.reports}
                      artifacts={message.artifacts}
                      jobId={message.jobId}
                    />
                  )}
                </div>
              </article>
            );
          })
        )}

        {loading && (
          <article className="chat-message-row assistant">
            <div className="message-avatar" aria-hidden="true">QA</div>
            <div className="message-content-wrapper">
              <ProcessingClock />
            </div>
          </article>
        )}

        <div ref={messagesEndRef} />
      </div>

      <footer className="chat-footer">
        <div className="footer-input-row">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Escribe una consulta sobre Jira o solicita un análisis..."
            rows={2}
            aria-label="Campo de mensaje para consulta"
          />
          <button
            type="button"
            className="send-message-button"
            disabled={!text.trim() || loading}
            onClick={handleSubmit}
            title="Enviar mensaje"
            aria-label="Enviar mensaje"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="footer-keyboard-hint">
          <span>Presiona <strong>Enter</strong> para enviar · <strong>Shift + Enter</strong> para salto de línea</span>
        </div>
      </footer>
    </main>
  );
}
