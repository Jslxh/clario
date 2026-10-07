import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTask } from '../context/TaskContext';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { MessageBubble } from '../components/chat/MessageBubble';

export const Chat = () => {
  const { user } = useAuth();
  const {
    conversations,
    activeConversationId,
    activeMessages,
    activeGenerations,
    isLoadingHistory,
    chatError,
    selectConversation,
    startNewChat,
    deleteConversation,
    sendChatMessage,
  } = useTask();

  const [inputQuery, setInputQuery] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const currentGen = activeGenerations[activeConversationId || 'new'];
  const isGenerating = Boolean(currentGen?.isGenerating);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeMessages, isGenerating]);

  // Submit question / message
  const handleSendMessage = async (e, forcedQuery = null) => {
    if (e) e.preventDefault();
    const query = (forcedQuery || inputQuery).trim();
    if (!query || isGenerating) return;

    setInputQuery('');
    sendChatMessage(query);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConversationId);
  const roleDepartment = user?.department || 'General';

  return (
    <div className="chat-page-container">
      {/* Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={selectConversation}
        onNewChat={startNewChat}
        onDeleteConversation={deleteConversation}
        isLoading={isLoadingHistory && conversations.length === 0}
      />

      {/* Main Chat Workspace */}
      <div className="chat-main-area">
        {/* Chat Header */}
        <header className="chat-header">
          <div className="chat-header-title-box">
            <h1 className="chat-title">
              {activeConv ? activeConv.title : 'Enterprise Knowledge Chat'}
            </h1>
            <span className="chat-subtitle">
              Grounded Question Answering &bull; Neon DB &bull; Qdrant Cloud &bull; NLI Verification
            </span>
          </div>

          <div className="chat-header-badges">
            {isGenerating && currentGen?.pid && (
              <span className="code-badge cyan-glow">
                <span className="pulse-dot active"></span>
                <span>{currentGen.pid} ({currentGen.thread})</span>
              </span>
            )}
            <span className="code-badge">{roleDepartment} Scope</span>
            <span className="status-pill success">● RAG Pipeline Online</span>
          </div>
        </header>

        {/* Global Error Banner */}
        {chatError && (
          <div className="auth-alert error chat-error-banner" role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{chatError}</span>
          </div>
        )}

        {/* Messages Stream */}
        <div className="chat-messages-scroll">
          {activeMessages.length === 0 && !isGenerating ? (
            <div className="chat-welcome-card">
              <div className="brand-icon-box large">C</div>
              <h2>Ask Clario Knowledge Base</h2>
              <p>
                Ask questions against authorized enterprise documents stored in the database.
                All responses are synthesized directly from retrieved passages and verified for factual grounding against source documents.
              </p>
            </div>
          ) : (
            <div className="messages-list">
              {activeMessages.map((msg, idx) => (
                <MessageBubble key={msg.id || idx} message={msg} />
              ))}

              {/* Generating / Loading indicator with Process ID & Thread */}
              {isGenerating && (
                <div className="message-row assistant-row generating-row">
                  <div className="avatar assistant-avatar">C</div>
                  <div className="message-bubble assistant-bubble generating-bubble">
                    <div className="generating-indicator">
                      <div className="dot"></div>
                      <div className="dot"></div>
                      <div className="dot"></div>
                      <span>
                        Synthesizing answer & verifying sources...{' '}
                        {currentGen?.pid && (
                          <strong className="gen-pid-tag">[{currentGen.pid}]</strong>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Query Input Box */}
        <div className="chat-input-container">
          <form onSubmit={handleSendMessage} className="chat-input-form">
            <textarea
              ref={inputRef}
              className="chat-textarea"
              placeholder={`Ask a question about ${roleDepartment} or company documents... (Press Enter)`}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isGenerating}
              id="chat-input-query"
            />

            <button
              type="submit"
              className="btn-primary btn-send-query"
              disabled={!inputQuery.trim() || isGenerating}
              id="btn-send-query"
              title="Send question to RAG pipeline"
            >
              {isGenerating ? (
                <span className="btn-spinner"></span>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </form>

          <div className="chat-input-caption">
            <span>Answers synthesized from retrieved passages &bull; Cross-Encoder Reranking &bull; NLI Grounding Verification</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
