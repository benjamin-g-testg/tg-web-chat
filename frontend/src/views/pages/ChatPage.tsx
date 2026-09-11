import ChatBox, { type Message } from "../../components/ChatBox";

/** Reusable page adapter; App composes the sidebar and this central chat view. */
export default function ChatPage({ messages, loading, onSend }: { messages: Message[]; loading: boolean; onSend: (text: string) => void }) {
  return <ChatBox messages={messages} loading={loading} onSend={onSend} />;
}
