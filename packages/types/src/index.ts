export type UserRole = 'user' | 'admin' | 'system';

export interface User {
  id: string;
  email: string;
  name?: string;
  avatarUrl?: string;
  role: UserRole;
  isVerified: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface UserProfile {
  userId: string;
  bio?: string;
  company?: string;
  website?: string;
  location?: string;
}

export interface UserPreferences {
  userId: string;
  theme: 'light' | 'dark' | 'system';
  sidebarOpen: boolean;
  fontSize: 'sm' | 'md' | 'lg';
  keyboardShortcutsEnabled: boolean;
  notificationsEnabled: boolean;
}

export interface Session {
  id: string;
  userId: string;
  token: string;
  expiresAt: string;
  ipAddress?: string;
  userAgent?: string;
  createdAt: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  ownerId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Folder {
  id: string;
  projectId: string;
  name: string;
  color?: string;
  isPinned: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Chat {
  id: string;
  folderId?: string | null;
  projectId: string;
  title: string;
  isPinned: boolean;
  isArchived: boolean;
  modelId: string;
  agentId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  chatId: string;
  role: MessageRole;
  content: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  latencyMs?: number;
  createdAt: string;
  updatedAt: string;
}

export interface FileAttachment {
  id: string;
  messageId?: string | null;
  chatId?: string | null;
  name: string;
  size: number;
  mimeType: string;
  url: string;
  status: 'uploading' | 'completed' | 'failed';
  progress: number;
  createdAt: string;
}

export interface Agent {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  systemPrompt: string;
  modelId: string;
  temperature: number;
  topP: number;
  maxTokens: number;
  createdAt: string;
  updatedAt: string;
}

export interface PromptTemplate {
  id: string;
  userId: string;
  name: string;
  content: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ModelConfig {
  id: string;
  provider: string; // e.g., 'bedrock', 'openai', 'anthropic'
  name: string;
  contextWindow: number;
  maxOutputTokens: number;
  isDefault: boolean;
}

export interface MemoryContext {
  id: string;
  userId: string;
  chatId?: string;
  key: string;
  value: string;
  confidenceScore: number;
  createdAt: string;
}

export interface KnowledgeDocument {
  id: string;
  workspaceId: string;
  name: string;
  filePath: string;
  chunkCount: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  createdAt: string;
}
