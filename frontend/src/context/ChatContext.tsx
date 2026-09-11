import { createContext, useContext } from "react";

/** Shared contract for future pages that need the current backend session. */
export const ChatSessionContext = createContext<string | undefined>(undefined);
export function useChatSession(): string | undefined { return useContext(ChatSessionContext); }
