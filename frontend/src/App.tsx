import { useState, useEffect } from "react";
import * as XLSX from "xlsx";
import Sidebar from "./components/Sidebar";
import ChatBox from "./components/ChatBox";
import ArtifactsModal from "./components/ArtifactsModal";
import {
  sendChatMessage,
  fetchSessions,
  fetchSessionDetail,
  renameSession,
  deleteSession,
  type ChatMessageItem,
  type SessionListItem,
} from "./services/api";

export default function App() {
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [history, setHistory] = useState<SessionListItem[]>([]);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isArtifactsOpen, setIsArtifactsOpen] = useState(false);

  // Cargar historial de sesiones ordenado al inicio
  useEffect(() => {
    fetchSessions()
      .then((sessions) => setHistory(sessions))
      .catch((error) => console.warn("No se pudieron cargar sesiones previas:", error));
  }, []);

  const handleSelectSession = async (selectedId: string) => {
    setLoading(true);
    try {
      const detail = await fetchSessionDetail(selectedId);
      setSessionId(detail.session.id);

      const formattedMessages: ChatMessageItem[] = detail.messages.map((m, idx) => {
        const isLastAssistant = m.role === "assistant" && idx === detail.messages.length - 1;
        return {
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
          reports: isLastAssistant && detail.reports ? detail.reports : undefined,
          metrics: isLastAssistant && detail.metrics ? detail.metrics : undefined,
          artifacts: isLastAssistant && detail.artifacts ? detail.artifacts : undefined,
          jobId: isLastAssistant && detail.job ? detail.job.id : undefined,
        };
      });

      setMessages(formattedMessages);
    } catch (error) {
      console.error("Error al cargar la sesión:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    setSessionId(undefined);
    setMessages([]);
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    try {
      const updated = await renameSession(id, newTitle);
      setHistory((prev) =>
        prev.map((item) => (item.id === id ? { ...item, title: updated.title } : item))
      );
    } catch (error) {
      console.error("Error al renombrar la sesión:", error);
      alert(error instanceof Error ? error.message : "Error al renombrar.");
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      setHistory((prev) => prev.filter((item) => item.id !== id));
      if (sessionId === id) {
        handleNewSession();
      }
    } catch (error) {
      console.error("Error al eliminar la sesión:", error);
      alert("No fue posible eliminar la sesión.");
    }
  };

  const handleSendMessage = async (content: string) => {
    const userTimestamp = new Date().toISOString();
    const tempUserMessage: ChatMessageItem = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: userTimestamp,
    };

    setMessages((prev) => [...prev, tempUserMessage]);
    setLoading(true);

    try {
      const response = await sendChatMessage({
        message: content,
        search_filter: "",
        analysis_requested: "",
        session_id: sessionId,
      });

      setSessionId(response.session.id);

      // Actualizar listado de historial si es nueva sesión
      setHistory((prev) => {
        const exists = prev.some((item) => item.id === response.session.id);
        if (exists) {
          return prev.map((item) =>
            item.id === response.session.id
              ? { ...item, updated_at: response.session.updated_at || new Date().toISOString() }
              : item
          );
        }
        return [
          {
            id: response.session.id,
            title: response.session.title,
            created_at: response.session.created_at || new Date().toISOString(),
            updated_at: response.session.updated_at || new Date().toISOString(),
            message_count: 2,
          },
          ...prev,
        ];
      });

      const assistantMessage: ChatMessageItem = {
        id: response.message.id,
        role: "assistant",
        content: response.message.content,
        timestamp: response.message.timestamp,
        reports: response.reports,
        metrics: response.metrics,
        artifacts: response.artifacts,
        jobId: response.job?.id,
        agent: response.agent,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessageItem = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: error instanceof Error ? error.message : "Error inesperado durante la ejecución.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadExcel = () => {
    const summaryRows = [
      {
        "ID Sesión": sessionId || "Actual",
        "Total Mensajes": messages.length,
        "Fecha de Exportación": new Date().toLocaleString("es-CL"),
      },
    ];

    const messagesRows = messages.map((m, index) => ({
      "#": index + 1,
      "Fecha/Hora": m.timestamp ? new Date(m.timestamp).toLocaleString("es-CL") : "N/A",
      "Rol": m.role === "user" ? "Usuario" : "Asistente QA",
      "Contenido": m.content,
      "Intención": m.agent?.intent || "-",
    }));

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(summaryRows), "Resumen Sesión");
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(messagesRows), "Historial Conversación");
    XLSX.writeFile(workbook, `reporte-jira-qa-${sessionId ? sessionId.slice(0, 8) : "sesion"}.xlsx`);
  };

  return (
    <div className="app-layout">
      <Sidebar
        history={history}
        currentSessionId={sessionId}
        onDownload={handleDownloadExcel}
        onOpenArtifacts={() => setIsArtifactsOpen(true)}
        onSelect={handleSelectSession}
        onNewSession={handleNewSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
      />
      <ChatBox
        messages={messages}
        loading={loading}
        onSend={handleSendMessage}
      />
      <ArtifactsModal
        isOpen={isArtifactsOpen}
        onClose={() => setIsArtifactsOpen(false)}
      />
    </div>
  );
}
