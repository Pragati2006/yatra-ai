import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import {
  parseMarkdownToElements as coreParseMarkdownToElements,
  renderInlineSpans as coreRenderInlineSpans,
  parseRowCells,
  getAlignments,
} from '../../utils/markdownParser';

export { coreRenderInlineSpans as renderInlineSpans };

/**
 * Enhanced, robust Markdown renderer for Yatra AI responses.
 * Renders headings (H1-H6), bold, italic, bold+italic, lists (unordered & ordered),
 * tables, code blocks with copy action, blockquotes, links, and inline styling.
 * 
 * Identifier safety: Protects technical identifiers (e.g. booking_id, pax_count)
 * and URLs from accidental italic/heading formatting.
 * Streaming resilience: Gracefully closes incomplete formatting tags during active streaming.
 */
export default function MarkdownContent({ content }) {
  if (!content) return null;

  const elements = coreParseMarkdownToElements(content, CodeBlock, MarkdownTable);

  return (
    <div
      className="yatra-markdown-body"
      style={{
        lineHeight: 1.62,
        color: 'var(--text-primary, #30272A)',
        fontSize: '0.94rem',
        wordBreak: 'break-word',
      }}
    >
      {elements}
    </div>
  );
}

/**
 * Reusable inline markdown helper for cards and previews.
 */
export function InlineMarkdown({ text }) {
  if (!text) return null;
  return <>{coreRenderInlineSpans(text)}</>;
}

export function parseMarkdownToElements(rawText) {
  return coreParseMarkdownToElements(rawText, CodeBlock, MarkdownTable);
}

function MarkdownTable({ headerRow, delimiterRow, dataRows }) {
  const headers = parseRowCells(headerRow);
  const alignments = getAlignments(delimiterRow);
  const numCols = Math.max(headers.length, alignments.length);

  return (
    <div
      className="chat-table-wrapper"
      style={{
        width: '100%',
        maxWidth: '100%',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
        margin: '0.75rem 0 1rem 0',
        border: '1px solid var(--border-default, #E9DED6)',
        borderRadius: '10px',
        background: 'var(--surface-white, #FFFCF9)',
        boxShadow: '0 2px 6px rgba(84, 21, 45, 0.04)',
      }}
    >
      <table
        className="chat-markdown-table"
        style={{
          width: '100%',
          minWidth: '420px',
          borderCollapse: 'collapse',
          fontSize: '0.84rem',
          textAlign: 'left',
        }}
      >
        <thead
          style={{
            background: 'var(--secondary-bg, #F2EAE4)',
            borderBottom: '2px solid var(--border-default, #E9DED6)',
          }}
        >
          <tr>
            {headers.map((h, idx) => (
              <th
                key={idx}
                style={{
                  padding: '9px 12px',
                  fontWeight: 700,
                  color: 'var(--royal-plum, #54152D)',
                  textAlign: alignments[idx] || 'left',
                  whiteSpace: 'nowrap',
                  fontSize: '0.82rem',
                  borderRight: idx === numCols - 1 ? 'none' : '1px solid var(--border-default, #E9DED6)',
                }}
              >
                {coreRenderInlineSpans(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((rowStr, rIdx) => {
            const cells = parseRowCells(rowStr);
            const rowBg = rIdx % 2 === 0 ? 'var(--surface-white, #FFFCF9)' : '#FDF9F6';
            return (
              <tr
                key={rIdx}
                style={{
                  background: rowBg,
                  borderBottom: rIdx === dataRows.length - 1 ? 'none' : '1px solid var(--border-default, #E9DED6)',
                }}
              >
                {Array.from({ length: numCols }).map((_, cIdx) => (
                  <td
                    key={cIdx}
                    style={{
                      padding: '8px 12px',
                      color: 'var(--text-primary, #30272A)',
                      textAlign: alignments[cIdx] || 'left',
                      fontSize: '0.83rem',
                      borderRight: cIdx === numCols - 1 ? 'none' : '1px solid var(--border-default, #E9DED6)',
                    }}
                  >
                    {coreRenderInlineSpans(cells[cIdx] || '')}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div
      style={{
        margin: '0.75rem 0',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid var(--border-default, #E9DED6)',
        background: '#200810',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '4px 10px',
          background: '#15040A',
          color: 'var(--champagne-taupe, #A3826C)',
          fontSize: '0.72rem',
          fontWeight: 600,
        }}
      >
        <span>{language ? language.toUpperCase() : 'CODE'}</span>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            background: copied ? '#28A745' : 'rgba(255, 255, 255, 0.12)',
            border: 'none',
            borderRadius: '4px',
            color: '#FFFFFF',
            padding: '2px 8px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          {copied ? (
            <>
              <Check size={11} />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy size={11} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '10px 12px',
          overflowX: 'auto',
          color: '#F7F1EB',
          fontFamily: 'monospace',
          fontSize: '0.82rem',
          lineHeight: 1.45,
        }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}
