/**
 * Chat Screen — AI chat with SSE streaming.
 *
 * Features:
 *  - Chat list sidebar (flat list with search)
 *  - Chat thread with streaming message display
 *  - Auto-scroll during streaming
 *  - Model indicator in input bar
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthStore } from '../../src/store/useAuthStore';
import { useChatStore, Chat, Message } from '../../src/store/useChatStore';
import { apiFetch, apiStream } from '../../src/lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../src/theme/tokens';

type ViewMode = 'list' | 'thread';

export default function ChatScreen() {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [input, setInput] = useState('');
  const { currentProject, fetchWorkspacesAndProjects } = useAuthStore();
  const {
    chats, currentChatId, messages, isGenerating, streamingContent,
    setChats, setCurrentChatId, setMessages, setIsGenerating,
    setStreamingContent, appendStreamingContent, addMessage,
    deleteChatFromStore,
  } = useChatStore();
  const flatListRef = useRef<FlatList>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    fetchWorkspacesAndProjects();
    Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
  }, [fadeAnim, fetchWorkspacesAndProjects]);

  // Fetch chats when project is available
  useEffect(() => {
    if (currentProject?.id) {
      apiFetch<Chat[]>(`/projects/${currentProject.id}/chats`)
        .then(setChats)
        .catch((e) => console.warn('Failed to fetch chats:', e));
    }
  }, [currentProject?.id, setChats]);

  // Fetch messages when a chat is selected
  useEffect(() => {
    if (currentChatId) {
      apiFetch<Message[]>(`/chats/${currentChatId}/messages`)
        .then(setMessages)
        .catch((e) => console.warn('Failed to fetch messages:', e));
    }
  }, [currentChatId, setMessages]);

  const createNewChat = async () => {
    if (!currentProject?.id) {
      Alert.alert('No Project', 'Please wait while we set up your workspace.');
      return;
    }

    try {
      const chat = await apiFetch<Chat>(`/projects/${currentProject.id}/chats`, {
        method: 'POST',
        json: {
          title: 'New Conversation',
          model_id: 'moonshotai.kimi-k2.5',
        },
      });
      setChats([chat, ...chats]);
      setCurrentChatId(chat.id);
      setViewMode('thread');
    } catch (err) {
      Alert.alert('Error', 'Failed to create chat');
    }
  };

  const openChat = (chatId: string) => {
    setCurrentChatId(chatId);
    setViewMode('thread');
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !currentChatId || isGenerating) return;

    setInput('');
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      chat_id: currentChatId,
      role: 'user',
      content: text,
    };
    addMessage(userMsg);

    setIsGenerating(true);
    setStreamingContent('');

    try {
      const stream = apiStream(`/chats/${currentChatId}/messages`, {
        method: 'POST',
        json: { content: text, model_id: 'moonshotai.kimi-k2.5' },
      });

      for await (const chunk of stream) {
        appendStreamingContent(chunk);
      }

      // Finalize: add the complete assistant message
      const finalContent = useChatStore.getState().streamingContent;
      addMessage({
        id: `assistant-${Date.now()}`,
        chat_id: currentChatId,
        role: 'assistant',
        content: finalContent,
      });
      setStreamingContent('');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Message failed';
      Alert.alert('Error', msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const deleteChat = async (chatId: string) => {
    try {
      await apiFetch(`/chats/${chatId}`, { method: 'DELETE' });
      deleteChatFromStore(chatId);
    } catch {
      Alert.alert('Error', 'Failed to delete chat');
    }
  };

  // Auto-scroll during streaming
  useEffect(() => {
    if (streamingContent) {
      flatListRef.current?.scrollToEnd({ animated: false });
    }
  }, [streamingContent]);

  // ── Chat List View ────────────────────────────────────────────────────────

  if (viewMode === 'list') {
    return (
      <View style={styles.container}>
        <LinearGradient
          colors={['#050507', '#080818', '#050507']}
          style={StyleSheet.absoluteFill}
        />
        <SafeAreaView style={styles.safeArea} edges={['top']}>
          <Animated.View style={[styles.inner, { opacity: fadeAnim }]}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.headerTitle}>Chat</Text>
              <Pressable
                style={({ pressed }) => [styles.newChatBtn, pressed && { opacity: 0.7 }]}
                onPress={createNewChat}
              >
                <Text style={styles.newChatBtnText}>+ New</Text>
              </Pressable>
            </View>

            {/* Chat List */}
            {chats.length === 0 ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyIcon}>◉</Text>
                <Text style={styles.emptyTitle}>No Conversations</Text>
                <Text style={styles.emptyText}>
                  Tap "New" to start a conversation with Kimi AI
                </Text>
              </View>
            ) : (
              <FlatList
                data={chats}
                keyExtractor={(item) => item.id}
                contentContainerStyle={styles.listContent}
                renderItem={({ item }) => (
                  <Pressable
                    style={({ pressed }) => [
                      styles.chatItem,
                      pressed && { backgroundColor: colors.bg.elevated },
                    ]}
                    onPress={() => openChat(item.id)}
                    onLongPress={() => {
                      Alert.alert('Delete Chat?', item.title, [
                        { text: 'Cancel', style: 'cancel' },
                        { text: 'Delete', style: 'destructive', onPress: () => deleteChat(item.id) },
                      ]);
                    }}
                  >
                    <Text style={styles.chatItemIcon}>◉</Text>
                    <View style={styles.chatItemContent}>
                      <Text style={styles.chatItemTitle} numberOfLines={1}>
                        {item.title}
                      </Text>
                      <Text style={styles.chatItemMeta}>
                        {item.updated_at
                          ? new Date(item.updated_at).toLocaleDateString()
                          : 'Just now'}
                      </Text>
                    </View>
                  </Pressable>
                )}
              />
            )}
          </Animated.View>
        </SafeAreaView>
      </View>
    );
  }

  // ── Chat Thread View ──────────────────────────────────────────────────────

  const allMessages = [
    ...messages,
    ...(streamingContent
      ? [{
          id: 'streaming',
          chat_id: currentChatId || '',
          role: 'assistant' as const,
          content: streamingContent,
        }]
      : []),
  ];

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#050507', '#080818', '#050507']}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <KeyboardAvoidingView
          style={styles.inner}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
        >
          {/* Thread Header */}
          <View style={styles.threadHeader}>
            <Pressable onPress={() => setViewMode('list')} style={styles.backButton}>
              <Text style={styles.backText}>← Back</Text>
            </Pressable>
            <Text style={styles.threadTitle} numberOfLines={1}>
              {chats.find((c) => c.id === currentChatId)?.title || 'Chat'}
            </Text>
          </View>

          {/* Messages */}
          <FlatList
            ref={flatListRef}
            data={allMessages}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.messagesContent}
            onContentSizeChange={() =>
              flatListRef.current?.scrollToEnd({ animated: true })
            }
            renderItem={({ item }) => (
              <View
                style={[
                  styles.messageBubble,
                  item.role === 'user'
                    ? styles.userBubble
                    : styles.assistantBubble,
                ]}
              >
                <Text
                  style={[
                    styles.messageText,
                    item.role === 'user'
                      ? styles.userText
                      : styles.assistantText,
                  ]}
                >
                  {item.content}
                </Text>
                {item.id === 'streaming' && (
                  <ActivityIndicator
                    size="small"
                    color={colors.accent.violet}
                    style={styles.streamDot}
                  />
                )}
              </View>
            )}
          />

          {/* Input Bar */}
          <View style={styles.inputBar}>
            <TextInput
              style={styles.chatInput}
              value={input}
              onChangeText={setInput}
              placeholder="Ask anything…"
              placeholderTextColor={colors.fg.faint}
              multiline
              maxLength={4000}
              editable={!isGenerating}
            />
            <Pressable
              style={({ pressed }) => [
                styles.sendButton,
                pressed && { opacity: 0.7 },
                (!input.trim() || isGenerating) && { opacity: 0.3 },
              ]}
              onPress={sendMessage}
              disabled={!input.trim() || isGenerating}
            >
              <Text style={styles.sendIcon}>↑</Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.deep },
  safeArea: { flex: 1 },
  inner: { flex: 1 },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing['2xl'],
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes['2xl'],
    color: colors.fg.primary,
    letterSpacing: -0.5,
  },
  newChatBtn: {
    backgroundColor: colors.accent.indigoMuted,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
  },
  newChatBtnText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.accent.indigo,
  },

  // Chat list
  listContent: { paddingHorizontal: spacing['2xl'] },
  chatItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
    marginBottom: spacing.xs,
  },
  chatItemIcon: {
    fontSize: 16,
    color: colors.fg.faint,
    marginRight: spacing.md,
  },
  chatItemContent: { flex: 1 },
  chatItemTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  chatItemMeta: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.faint,
    marginTop: 2,
  },

  // Empty
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing['4xl'],
  },
  emptyIcon: { fontSize: 48, color: colors.fg.faint, marginBottom: spacing.lg },
  emptyTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
  },

  // Thread header
  threadHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.bg.elevated,
  },
  backButton: { marginRight: spacing.md },
  backText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.base,
    color: colors.accent.indigo,
  },
  threadTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.md,
    color: colors.fg.primary,
    flex: 1,
  },

  // Messages
  messagesContent: {
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
  },
  messageBubble: {
    maxWidth: '85%',
    padding: spacing.lg,
    borderRadius: radii.lg,
    marginBottom: spacing.md,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: colors.accent.indigoMuted,
    borderBottomRightRadius: radii.sm,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: colors.bg.glass,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderBottomLeftRadius: radii.sm,
  },
  messageText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    lineHeight: 22,
  },
  userText: { color: colors.fg.primary },
  assistantText: { color: colors.fg.secondary },
  streamDot: { marginTop: spacing.sm, alignSelf: 'flex-start' },

  // Input bar
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.bg.elevated,
    backgroundColor: 'rgba(5, 5, 7, 0.9)',
  },
  chatInput: {
    flex: 1,
    backgroundColor: colors.bg.card,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.elevated,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
    maxHeight: 120,
    marginRight: spacing.md,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: radii.full,
    backgroundColor: colors.accent.indigo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendIcon: {
    fontSize: 20,
    color: '#fff',
    fontWeight: '700',
  },
});
