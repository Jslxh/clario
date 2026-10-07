import React from 'react';
import { CitationCard } from './CitationCard';
import { VerificationBadge } from './VerificationBadge';
import { MarkdownContent } from './MarkdownContent';

export const MessageBubble = ({ message }) => {
  if (!message) return null;

  const isUser = message.role === 'user';
  const content = message.content || '';
  const timestamp = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  // Extract nested generation payload if available (from conversation turn or direct query response)
  const gen = message.generation || {};
  const citations = message.citations || gen.citations || [];
  const verification = message.verification || gen.verification || null;
  const hasSufficientContext =
    message.has_sufficient_context !== undefined
      ? message.has_sufficient_context
      : gen.has_sufficient_context !== undefined
      ? gen.has_sufficient_context
      : true;

  const latencyMs = message.latency_ms || gen.latency_ms;
  const modelName = message.model_name || gen.model_name;
  const retrievalMode = message.retrieval_mode || gen.retrieval_mode;
  const processId = message.process_id || gen.process_id;

  if (isUser) {
    return (
      <div className="message-row user-row">
        <div className="message-bubble user-bubble">
          <div className="message-content">{content}</div>
          {timestamp && <div className="message-time">{timestamp}</div>}
        </div>
        <div className="avatar user-avatar" title="You">
          U
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant-row">
      <div className="avatar assistant-avatar" title="Clario Intelligence">
        C
      </div>
      <div className="message-bubble assistant-bubble">
        {/* Abstention Banner if insufficient context */}
        {!hasSufficientContext && (
          <div className="abstention-banner">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>
              I could not find sufficient information in the provided documentation to answer your question.
            </span>
          </div>
        )}

        {/* ChatGPT Markdown Answer Content */}
        <div className="message-content assistant-content">
          <MarkdownContent content={content} />
        </div>

        {/* Citations */}
        {citations && citations.length > 0 && <CitationCard citations={citations} />}

        {/* Grounding Verification */}
        {verification && <VerificationBadge verification={verification} />}

        {/* Generation Metadata Footer with Process ID */}
        {(modelName || retrievalMode || latencyMs || processId) && (
          <div className="generation-meta-footer">
            {processId && <span className="meta-tag proc-id-badge">PID: {processId}</span>}
            {modelName && <span className="meta-tag">Model: {modelName}</span>}
            {retrievalMode && <span className="meta-tag">Mode: {retrievalMode}</span>}
            {latencyMs !== undefined && latencyMs !== null && (
              <span className="meta-tag">Latency: {Math.round(latencyMs)}ms</span>
            )}
            {timestamp && <span className="meta-tag time">{timestamp}</span>}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;

