/**
 * Chat Store — manages chat state for the mobile app.
 *
 * Port of apps/web/src/store/useChatStore.ts.
 */

import { create } from 'zustand';

export interface Chat {
  id: string;
  title: string;
  model_id: string;
  project_id: string;
  folder_id?: string | null;
  agent_id?: string | null;
  is_pinned?: boolean;
  is_archived?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

export interface ModelConfig {
  id: string;
  provider: string;
  name: string;
  contextWindow: number;
  maxOutputTokens: number;
  isDefault: boolean;
}

interface ChatState {
  chats: Chat[];
  currentChatId: string | null;
  messages: Message[];
  models: ModelConfig[];
  selectedModelId: string;
  isGenerating: boolean;
  streamingContent: string;
  searchQuery: string;

  setChats: (chats: Chat[]) => void;
  setCurrentChatId: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  setModels: (models: ModelConfig[]) => void;
  setSelectedModelId: (id: string) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (chunk: string) => void;
  setSearchQuery: (query: string) => void;
  addMessage: (message: Message) => void;
  updateMessageContent: (messageId: string, content: string) => void;
  renameChatInStore: (chatId: string, title: string) => void;
  deleteChatFromStore: (chatId: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chats: [],
  currentChatId: null,
  messages: [],
  models: [
    {
      id: 'moonshotai.kimi-k2.5',
      provider: 'bedrock',
      name: 'Kimi K2.5 (Amazon Bedrock)',
      contextWindow: 262144,
      maxOutputTokens: 16384,
      isDefault: true,
    },
  ],
  selectedModelId: 'moonshotai.kimi-k2.5',
  isGenerating: false,
  streamingContent: '',
  searchQuery: '',

  setChats: (chats) => set({ chats }),
  setCurrentChatId: (currentChatId) =>
    set({ currentChatId, messages: [], streamingContent: '' }),
  setMessages: (messages) => set({ messages }),
  setModels: (models) => set({ models }),
  setSelectedModelId: (selectedModelId) => set({ selectedModelId }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setStreamingContent: (streamingContent) => set({ streamingContent }),
  appendStreamingContent: (chunk) =>
    set((state) => ({ streamingContent: state.streamingContent + chunk })),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateMessageContent: (messageId, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content } : m,
      ),
    })),
  renameChatInStore: (chatId, title) =>
    set((state) => ({
      chats: state.chats.map((c) => (c.id === chatId ? { ...c, title } : c)),
    })),
  deleteChatFromStore: (chatId) =>
    set((state) => ({
      chats: state.chats.filter((c) => c.id !== chatId),
      currentChatId: state.currentChatId === chatId ? null : state.currentChatId,
    })),
}));
