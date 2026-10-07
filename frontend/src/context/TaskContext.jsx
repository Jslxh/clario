import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '../api/client';
import { generateProcessId } from '../utils/processManager';

export { generateProcessId };

const TaskContext = createContext(null);

export const TaskProvider = ({ children }) => {
  // Global Task / Thread Registry
  const [tasks, setTasks] = useState([]);
  const [isProcessDrawerOpen, setIsProcessDrawerOpen] = useState(false);
  const [globalNotification, setGlobalNotification] = useState(null);

  // Persistent Chat State (Preserved across page navigations)
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [conversationMessagesCache, setConversationMessagesCache] = useState({});
  const [activeGenerations, setActiveGenerations] = useState({}); // { [convId || 'new']: { isGenerating, pid, thread, query, optimisticMsg } }
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [chatError, setChatError] = useState('');

  // Persistent Document Processing State
  const [processingDocIds, setProcessingDocIds] = useState(new Set());
  const activePollersRef = useRef(new Map()); // docId -> interval/timeout ID

  const showGlobalNotification = useCallback((message, type = 'success', pid = null) => {
    setGlobalNotification({ message, type, pid, id: Date.now() });
    setTimeout(() => {
      setGlobalNotification((curr) => (curr?.message === message ? null : curr));
    }, 5000);
  }, []);

  // Spawn an asynchronous background task with dedicated Process ID and Thread Worker
  const spawnTask = useCallback(async ({ type, thread, title, meta = {}, taskFn }) => {
    const pid = generateProcessId();
    const threadName = thread || `Worker-Thread-${Math.floor(Math.random() * 900 + 100)}`;
    const startTime = Date.now();

    const newTask = {
      id: pid,
      type,
      thread: threadName,
      title,
      status: 'RUNNING',
      startTime,
      endTime: null,
      durationMs: 0,
      meta,
      error: null,
    };

    setTasks((prev) => [newTask, ...prev.slice(0, 49)]);

    try {
      const result = await taskFn(pid);
      const endTime = Date.now();
      const durationMs = endTime - startTime;

      setTasks((prev) =>
        prev.map((t) =>
          t.id === pid
            ? { ...t, status: 'COMPLETED', endTime, durationMs, result }
            : t
        )
      );
      return { pid, result };
    } catch (err) {
      const endTime = Date.now();
      const durationMs = endTime - startTime;
      const errorMsg = err.message || 'Task execution failed';

      setTasks((prev) =>
        prev.map((t) =>
          t.id === pid
            ? { ...t, status: 'FAILED', endTime, durationMs, error: errorMsg }
            : t
        )
      );
      throw err;
    }
  }, []);

  // =========================================================================
  // PERSISTENT CHAT & GROUNDED RAG ASYNC WORKER
  // =========================================================================

  const loadConversations = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const list = await apiClient.listConversations();
      setConversations(Array.isArray(list) ? list : []);
    } catch (err) {
      console.warn('Failed to load conversation history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Initial load of conversations
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const selectConversation = useCallback(async (convId) => {
    if (!convId) {
      setActiveConversationId(null);
      return;
    }
    setActiveConversationId(convId);
    setChatError('');

    // If already cached, no need to re-fetch immediately
    if (conversationMessagesCache[convId]) {
      return;
    }

    setIsLoadingHistory(true);
    try {
      const conv = await apiClient.getConversation(convId);
      const rawMessages = Array.isArray(conv.messages) ? conv.messages : [];
      setConversationMessagesCache((prev) => ({
        ...prev,
        [convId]: rawMessages,
      }));
    } catch (err) {
      setChatError(err.message || 'Failed to load conversation messages.');
    } finally {
      setIsLoadingHistory(false);
    }
  }, [conversationMessagesCache]);

  const startNewChat = useCallback(() => {
    setActiveConversationId(null);
    setChatError('');
  }, []);

  const deleteConversation = useCallback(async (convId) => {
    try {
      await apiClient.deleteConversation(convId);
      setConversationMessagesCache((prev) => {
        const updated = { ...prev };
        delete updated[convId];
        return updated;
      });
      if (activeConversationId === convId) {
        startNewChat();
      }
      await loadConversations();
    } catch (err) {
      setChatError(`Failed to delete conversation: ${err.message}`);
    }
  }, [activeConversationId, startNewChat, loadConversations]);

  // Submit query asynchronously (Persists across route navigations!)
  const sendChatMessage = useCallback(async (queryText, forcedQuery = null) => {
    const query = (forcedQuery || queryText).trim();
    if (!query) return;

    const targetConvId = activeConversationId || 'new';
    const tempMsgId = `temp-${Date.now()}`;
    const optimisticUserMsg = {
      id: tempMsgId,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };

    // Add optimistic message to cache immediately
    setConversationMessagesCache((prev) => {
      const existing = prev[targetConvId] || [];
      return {
        ...prev,
        [targetConvId]: [...existing, optimisticUserMsg],
      };
    });

    const threadName = `Thread-LLM-RAG-${Math.floor(Math.random() * 900 + 100)}`;
    const pid = generateProcessId('PID-LLM');

    // Register active generation state
    setActiveGenerations((prev) => ({
      ...prev,
      [targetConvId]: {
        isGenerating: true,
        pid,
        thread: threadName,
        query,
        optimisticMsg: optimisticUserMsg,
        startTime: Date.now(),
      },
    }));

    // Spawn async background task
    spawnTask({
      type: 'llm_query',
      thread: threadName,
      title: `Grounded RAG: "${query.slice(0, 42)}${query.length > 42 ? '...' : ''}"`,
      meta: { conversationId: activeConversationId, query },
      taskFn: async (taskPid) => {
        try {
          let effectiveConvId = activeConversationId;

          // If new conversation, create it first
          if (!effectiveConvId) {
            const titleWords = query.split(/\s+/).slice(0, 6).join(' ');
            const initialTitle = titleWords.length > 50 ? `${titleWords.slice(0, 47)}...` : titleWords;
            const newConv = await apiClient.createConversation(initialTitle || 'New Conversation');
            effectiveConvId = newConv.id;
            setActiveConversationId(effectiveConvId);
          }

          const res = await apiClient.postMessage(effectiveConvId, {
            content: query,
            top_k: 5,
            verify: true,
          });

          const assistantMsg = {
            ...res.assistant_message,
            generation: res.generation || {},
            citations: res.generation?.citations || [],
            verification: res.generation?.verification || null,
            has_sufficient_context: res.generation?.has_sufficient_context !== false,
            latency_ms: res.generation?.latency_ms,
            model_name: res.generation?.model_name,
            retrieval_mode: res.generation?.retrieval_mode,
            process_id: taskPid,
          };

          setConversationMessagesCache((prev) => {
            const existing = prev[effectiveConvId] || prev['new'] || [];
            const filtered = existing.filter((m) => m.id !== tempMsgId);
            return {
              ...prev,
              [effectiveConvId]: [
                ...filtered,
                res.user_message || optimisticUserMsg,
                assistantMsg,
              ],
            };
          });

          await loadConversations();
          showGlobalNotification(`Answer synthesized for "${query.slice(0, 30)}..."`, 'info', taskPid);
          return assistantMsg;
        } finally {
          setActiveGenerations((prev) => {
            const updated = { ...prev };
            delete updated[targetConvId];
            delete updated['new'];
            return updated;
          });
        }
      },
    }).catch((err) => {
      setChatError(err.message || 'Failed to generate answer from knowledge base.');
      showGlobalNotification(`Query failed: ${err.message}`, 'error', pid);
    });
  }, [activeConversationId, spawnTask, loadConversations, showGlobalNotification]);

  // =========================================================================
  // PERSISTENT DOCUMENT INGESTION & PROCESSING ASYNC WORKER
  // =========================================================================

  const dispatchDocumentProcess = useCallback((documentId, docTitle = 'Document') => {
    if (!documentId) return;

    setProcessingDocIds((prev) => new Set(prev).add(documentId));
    const threadName = `Thread-Doc-Worker-${Math.floor(Math.random() * 900 + 100)}`;
    const pid = generateProcessId('PID-DOC');

    spawnTask({
      type: 'doc_process',
      thread: threadName,
      title: `Ingesting & Embedding: ${docTitle}`,
      meta: { documentId, docTitle },
      taskFn: async (taskPid) => {
        // Trigger ingestion dispatch
        await apiClient.processDocument(documentId);
        showGlobalNotification(`Document ingestion dispatched for "${docTitle}"`, 'info', taskPid);

        // Background polling loop across page transitions
        return new Promise((resolve, reject) => {
          let pollCycle = 0;
          const maxCycles = 30;

          const interval = setInterval(async () => {
            pollCycle += 1;
            try {
              const doc = await apiClient.getDocument(documentId);
              if (doc.status === 'READY') {
                clearInterval(interval);
                activePollersRef.current.delete(documentId);
                setProcessingDocIds((prev) => {
                  const updated = new Set(prev);
                  updated.delete(documentId);
                  return updated;
                });
                showGlobalNotification(`"${doc.title || doc.filename}" processed & indexed successfully!`, 'success', taskPid);
                resolve(doc);
              } else if (doc.status === 'FAILED') {
                clearInterval(interval);
                activePollersRef.current.delete(documentId);
                setProcessingDocIds((prev) => {
                  const updated = new Set(prev);
                  updated.delete(documentId);
                  return updated;
                });
                showGlobalNotification(`Document processing failed for "${docTitle}"`, 'error', taskPid);
                reject(new Error('Document ingestion and vector indexing failed.'));
              } else if (pollCycle >= maxCycles) {
                clearInterval(interval);
                activePollersRef.current.delete(documentId);
                setProcessingDocIds((prev) => {
                  const updated = new Set(prev);
                  updated.delete(documentId);
                  return updated;
                });
                resolve(doc);
              }
            } catch (pollErr) {
              clearInterval(interval);
              activePollersRef.current.delete(documentId);
              reject(pollErr);
            }
          }, 2500);

          activePollersRef.current.set(documentId, interval);
        });
      },
    }).catch((err) => {
      setProcessingDocIds((prev) => {
        const updated = new Set(prev);
        updated.delete(documentId);
        return updated;
      });
      showGlobalNotification(`Document processing failed: ${err.message}`, 'error', pid);
    });
  }, [spawnTask, showGlobalNotification]);

  // Clean up pollers on unmount
  useEffect(() => {
    return () => {
      activePollersRef.current.forEach((intervalId) => clearInterval(intervalId));
      activePollersRef.current.clear();
    };
  }, []);

  const runningTasks = tasks.filter((t) => t.status === 'RUNNING');
  const activeProcessesCount = runningTasks.length;

  const value = {
    tasks,
    runningTasks,
    activeProcessesCount,
    isProcessDrawerOpen,
    openProcessDrawer: () => setIsProcessDrawerOpen(true),
    closeProcessDrawer: () => setIsProcessDrawerOpen(false),
    toggleProcessDrawer: () => setIsProcessDrawerOpen((p) => !p),
    globalNotification,
    dismissGlobalNotification: () => setGlobalNotification(null),
    spawnTask,

    // Chat context
    conversations,
    activeConversationId,
    activeMessages: conversationMessagesCache[activeConversationId || 'new'] || [],
    conversationMessagesCache,
    activeGenerations,
    isLoadingHistory,
    chatError,
    setChatError,
    loadConversations,
    selectConversation,
    startNewChat,
    deleteConversation,
    sendChatMessage,

    // Document processing
    processingDocIds,
    dispatchDocumentProcess,
  };

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>;
};

export const useTask = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTask must be used within a TaskProvider');
  }
  return context;
};

export default TaskContext;
