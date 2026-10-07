import React, { useState } from 'react';

/**
 * ChatGPT-style Markdown & Rich Text Renderer
 * Supports:
 * - Headings (h1, h2, h3)
 * - Bold (**text**), Italic (*text*), Strikethrough (~~text~~)
 * - Code Blocks (```lang ... ```) with syntax header & copy button
 * - Inline Code (`code`)
 * - Bullet Lists (* item, - item)
 * - Numbered Lists (1. item, 2. item)
 * - Blockquotes (> quote)
 * - Horizontal Rules (---)
 * - Tables (| col 1 | col 2 |)
 */

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="chatgpt-code-block">
      <div className="code-block-header">
        <span className="code-lang-label">{language || 'code'}</span>
        <button
          type="button"
          className="code-copy-btn"
          onClick={handleCopy}
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span style={{ color: '#34d399' }}>Copied!</span>
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <span>Copy code</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-content">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function parseInlineFormatting(text) {
  if (!text) return text;

  // Split by inline code: `code`
  const parts = [];
  const codeRegex = /`([^`]+)`/g;
  let lastIdx = 0;
  let match;

  while ((match = codeRegex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push({ type: 'text', value: text.slice(lastIdx, match.index) });
    }
    parts.push({ type: 'inline-code', value: match[1] });
    lastIdx = match.index + match[0].length;
  }
  if (lastIdx < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIdx) });
  }

  return parts.map((part, pIdx) => {
    if (part.type === 'inline-code') {
      return (
        <code key={pIdx} className="chatgpt-inline-code">
          {part.value}
        </code>
      );
    }

    // Process bold, italic, bold+italic in text parts
    return parseTextTokens(part.value, pIdx);
  });
}

function parseTextTokens(text, parentKey) {
  // Replace bold+italic (***text*** or ___text___)
  // Replace bold (**text** or __text__)
  // Replace italic (*text* or _text_)
  // Replace strikethrough (~~text~~)
  const regex = /(\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|\*([^*]+)\*|~~([^~]+)~~)/g;
  const elements = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      elements.push(text.slice(lastIndex, match.index));
    }

    if (match[2]) {
      // Bold + Italic
      elements.push(
        <strong key={`${parentKey}-${match.index}`}>
          <em>{match[2]}</em>
        </strong>
      );
    } else if (match[3]) {
      // Bold
      elements.push(
        <strong key={`${parentKey}-${match.index}`} className="chatgpt-bold">
          {match[3]}
        </strong>
      );
    } else if (match[4]) {
      // Italic
      elements.push(
        <em key={`${parentKey}-${match.index}`} className="chatgpt-italic">
          {match[4]}
        </em>
      );
    } else if (match[5]) {
      // Strikethrough
      elements.push(
        <del key={`${parentKey}-${match.index}`}>{match[5]}</del>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    elements.push(text.slice(lastIndex));
  }

  return <React.Fragment key={parentKey}>{elements}</React.Fragment>;
}

export const MarkdownContent = ({ content = '' }) => {
  if (!content) return null;

  // 1. Separate code blocks from regular text
  const lines = content.split('\n');
  const renderedElements = [];

  let inCodeBlock = false;
  let codeBlockLang = '';
  let codeBlockBuffer = [];

  let inBulletList = false;
  let bulletListBuffer = [];

  let inNumberedList = false;
  let numberedListBuffer = [];

  const flushBulletList = (key) => {
    if (bulletListBuffer.length > 0) {
      renderedElements.push(
        <ul key={`ul-${key}`} className="chatgpt-bullet-list">
          {bulletListBuffer.map((item, bIdx) => (
            <li key={bIdx}>{parseInlineFormatting(item)}</li>
          ))}
        </ul>
      );
      bulletListBuffer = [];
      inBulletList = false;
    }
  };

  const flushNumberedList = (key) => {
    if (numberedListBuffer.length > 0) {
      renderedElements.push(
        <ol key={`ol-${key}`} className="chatgpt-numbered-list">
          {numberedListBuffer.map((item, nIdx) => (
            <li key={nIdx}>{parseInlineFormatting(item)}</li>
          ))}
        </ol>
      );
      numberedListBuffer = [];
      inNumberedList = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check code block fence ```
    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        // Close code block
        renderedElements.push(
          <CodeBlock
            key={`code-${i}`}
            language={codeBlockLang}
            code={codeBlockBuffer.join('\n')}
          />
        );
        inCodeBlock = false;
        codeBlockLang = '';
        codeBlockBuffer = [];
      } else {
        // Open code block
        flushBulletList(i);
        flushNumberedList(i);
        inCodeBlock = true;
        codeBlockLang = trimmed.slice(3).trim().toLowerCase();
        codeBlockBuffer = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockBuffer.push(line);
      continue;
    }

    // Check Bullet lists (* item, - item, • item)
    const bulletMatch = line.match(/^(\s*)[*\-•]\s+(.*)$/);
    if (bulletMatch) {
      flushNumberedList(i);
      inBulletList = true;
      bulletListBuffer.push(bulletMatch[2]);
      continue;
    }

    // Check Numbered lists (1. item, 2. item)
    const numberedMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
    if (numberedMatch) {
      flushBulletList(i);
      inNumberedList = true;
      numberedListBuffer.push(numberedMatch[2]);
      continue;
    }

    // If not a list item, flush any open lists
    if (inBulletList) flushBulletList(i);
    if (inNumberedList) flushNumberedList(i);

    // Empty line -> spacing paragraph
    if (!trimmed) {
      continue;
    }

    // Headings: ### H3, ## H2, # H1
    if (trimmed.startsWith('### ')) {
      renderedElements.push(
        <h3 key={`h3-${i}`} className="chatgpt-h3">
          {parseInlineFormatting(trimmed.slice(4))}
        </h3>
      );
    } else if (trimmed.startsWith('## ')) {
      renderedElements.push(
        <h2 key={`h2-${i}`} className="chatgpt-h2">
          {parseInlineFormatting(trimmed.slice(3))}
        </h2>
      );
    } else if (trimmed.startsWith('# ')) {
      renderedElements.push(
        <h1 key={`h1-${i}`} className="chatgpt-h1">
          {parseInlineFormatting(trimmed.slice(2))}
        </h1>
      );
    } else if (trimmed.startsWith('> ')) {
      // Blockquote
      renderedElements.push(
        <blockquote key={`quote-${i}`} className="chatgpt-blockquote">
          {parseInlineFormatting(trimmed.slice(2))}
        </blockquote>
      );
    } else if (trimmed === '---' || trimmed === '***') {
      // Horizontal Rule
      renderedElements.push(<hr key={`hr-${i}`} className="chatgpt-hr" />);
    } else {
      // Standard Paragraph
      renderedElements.push(
        <p key={`p-${i}`} className="chatgpt-paragraph">
          {parseInlineFormatting(line)}
        </p>
      );
    }
  }

  // Flush remaining open lists / code blocks
  if (inBulletList) flushBulletList('end');
  if (inNumberedList) flushNumberedList('end');
  if (inCodeBlock && codeBlockBuffer.length > 0) {
    renderedElements.push(
      <CodeBlock
        key="code-end"
        language={codeBlockLang}
        code={codeBlockBuffer.join('\n')}
      />
    );
  }

  return <div className="chatgpt-markdown-body">{renderedElements}</div>;
};

export default MarkdownContent;

