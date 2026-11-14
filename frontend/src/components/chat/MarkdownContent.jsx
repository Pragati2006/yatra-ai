import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

/**
 * Enhanced, robust Markdown renderer for Yatra AI responses.
 * Renders headings, lists, tables, code blocks with copy action, blockquotes,
 * links, and inline styling without third-party dependencies.
 */
export default function MarkdownContent({ content }) {
  if (!content) return null;

  const elements = parseMarkdownToElements(content);

  return (
    <div className="yatra-markdown-body" style={{ lineHeight: 1.6, color: 'var(--text-dark, #2A2020)', fontSize: '0.92rem' }}>
      {elements}
    </div>
  );
}

function parseMarkdownToElements(rawText) {
  const lines = rawText.split('\n');
  const elements = [];
  let index = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Empty lines
    if (!trimmed) {
      continue;
    }

    // 2. Code blocks (```language ... ```)
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <CodeBlock key={`code-${index++}`} code={codeLines.join('\n')} language={lang} />
      );
      continue;
    }

    // 3. Horizontal Rule
    if (/^(---|___|\*\*\*)$/.test(trimmed)) {
      elements.push(
        <hr
          key={`hr-${index++}`}
          style={{
            border: 'none',
            borderTop: '1px solid var(--gold-border, #E5D2AD)',
            margin: '1rem 0',
          }}
        />
      );
      continue;
    }

    // 4. Headings
    const h1Match = trimmed.match(/^#\s+(.+)$/);
    if (h1Match) {
      elements.push(
        <h2
          key={`h1-${index++}`}
          style={{
            fontFamily: 'var(--font-serif, Cinzel, serif)',
            fontSize: '1.25rem',
            fontWeight: 800,
            color: 'var(--burgundy, #58111A)',
            margin: '1.2rem 0 0.5rem',
            lineHeight: 1.3,
          }}
        >
          {renderInlineSpans(h1Match[1])}
        </h2>
      );
      continue;
    }

    const h2Match = trimmed.match(/^##\s+(.+)$/);
    if (h2Match) {
      elements.push(
        <h3
          key={`h2-${index++}`}
          style={{
            fontFamily: 'var(--font-serif, Cinzel, serif)',
            fontSize: '1.12rem',
            fontWeight: 800,
            color: 'var(--burgundy, #58111A)',
            margin: '1rem 0 0.4rem',
            lineHeight: 1.3,
          }}
        >
          {renderInlineSpans(h2Match[1])}
        </h3>
      );
      continue;
    }

    const h3Match = trimmed.match(/^###\s+(.+)$/);
    if (h3Match) {
      elements.push(
        <h4
          key={`h3-${index++}`}
          style={{
            fontFamily: 'var(--font-serif, Cinzel, serif)',
            fontSize: '1rem',
            fontWeight: 700,
            color: 'var(--burgundy, #58111A)',
            margin: '0.85rem 0 0.35rem',
            lineHeight: 1.3,
          }}
        >
          {renderInlineSpans(h3Match[1])}
        </h4>
      );
      continue;
    }

    // 5. Blockquotes (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines = [trimmed.replace(/^>\s?/, '')];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('>')) {
        i++;
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
      }
      elements.push(
        <blockquote
          key={`quote-${index++}`}
          style={{
            borderLeft: '3px solid var(--gold-primary, #B8860B)',
            background: 'var(--bg-subtle, #F8F4EC)',
            margin: '0.75rem 0',
            padding: '0.5rem 0.85rem',
            borderRadius: '0 8px 8px 0',
            fontStyle: 'italic',
            color: 'var(--burgundy-dark, #3D0810)',
          }}
        >
          {quoteLines.map((ql, qIdx) => (
            <p key={qIdx} style={{ margin: qIdx > 0 ? '0.35rem 0 0' : 0 }}>
              {renderInlineSpans(ql)}
            </p>
          ))}
        </blockquote>
      );
      continue;
    }

    // 6. Tables (| col1 | col2 |)
    if (trimmed.includes('|') && i + 1 < lines.length && isTableDelimiterRow(lines[i + 1])) {
      const headerRow = trimmed;
      const delimiterRow = lines[i + 1].trim();
      i += 2;
      const dataRows = [];
      while (i < lines.length && lines[i].trim().includes('|')) {
        const curLine = lines[i].trim();
        if (curLine.startsWith('#') || curLine.startsWith('```') || /^(---|___|\*\*\*)$/.test(curLine)) {
          break;
        }
        dataRows.push(curLine);
        i++;
      }
      i--; // adjust loop counter

      elements.push(
        <MarkdownTable
          key={`table-${index++}`}
          headerRow={headerRow}
          delimiterRow={delimiterRow}
          dataRows={dataRows}
        />
      );
      continue;
    }

    // 7. Unordered Lists (- , * , • )
    const ulMatch = trimmed.match(/^[•\-*]\s+(.+)$/);
    if (ulMatch) {
      const listItems = [ulMatch[1]];
      while (i + 1 < lines.length) {
        const nextTrimmed = lines[i + 1].trim();
        const nextUlMatch = nextTrimmed.match(/^[•\-*]\s+(.+)$/);
        if (nextUlMatch) {
          listItems.push(nextUlMatch[1]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ul
          key={`ul-${index++}`}
          style={{
            margin: '0.5rem 0 0.75rem 1.4rem',
            paddingLeft: 0,
            listStyleType: 'disc',
          }}
        >
          {listItems.map((item, liIdx) => (
            <li key={liIdx} style={{ margin: '0.25rem 0', lineHeight: 1.5 }}>
              {renderInlineSpans(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 8. Ordered Lists (1. ...)
    const olMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (olMatch) {
      const listItems = [olMatch[2]];
      while (i + 1 < lines.length) {
        const nextTrimmed = lines[i + 1].trim();
        const nextOlMatch = nextTrimmed.match(/^(\d+)\.\s+(.+)$/);
        if (nextOlMatch) {
          listItems.push(nextOlMatch[2]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ol
          key={`ol-${index++}`}
          style={{
            margin: '0.5rem 0 0.75rem 1.4rem',
            paddingLeft: 0,
          }}
        >
          {listItems.map((item, liIdx) => (
            <li key={liIdx} style={{ margin: '0.25rem 0', lineHeight: 1.5 }}>
              {renderInlineSpans(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 9. Standard Paragraph
    elements.push(
      <p key={`p-${index++}`} style={{ margin: '0 0 0.65rem 0', lineHeight: 1.58 }}>
        {renderInlineSpans(trimmed)}
      </p>
    );
  }

  return elements;
}

/**
 * Checks if a row is a valid markdown table delimiter row (e.g. |---|:---:|---:|)
 */
function isTableDelimiterRow(str) {
  if (!str || !str.includes('-')) return false;
  const content = str.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells = content.split('|');
  if (cells.length === 0) return false;
  return cells.every((cell) => /^\s*:?-+:?\s*$/.test(cell));
}

function parseRowCells(str) {
  let content = str.trim();
  if (content.startsWith('|')) content = content.substring(1);
  if (content.endsWith('|')) content = content.substring(0, content.length - 1);
  return content.split('|').map((c) => c.trim());
}

function getAlignments(delimiterRow) {
  const cells = parseRowCells(delimiterRow);
  return cells.map((cell) => {
    const trimmed = cell.trim();
    const startsColon = trimmed.startsWith(':');
    const endsColon = trimmed.endsWith(':');
    if (startsColon && endsColon) return 'center';
    if (endsColon) return 'right';
    return 'left';
  });
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
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '10px',
        background: '#FFFFFF',
        boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
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
        <thead style={{ background: 'var(--bg-subtle, #F8F4EC)', borderBottom: '2px solid var(--gold-border, #E5D2AD)' }}>
          <tr>
            {headers.map((h, idx) => (
              <th
                key={idx}
                style={{
                  padding: '9px 12px',
                  fontWeight: 700,
                  color: 'var(--burgundy, #58111A)',
                  textAlign: alignments[idx] || 'left',
                  whiteSpace: 'nowrap',
                  fontSize: '0.82rem',
                  borderRight: idx === numCols - 1 ? 'none' : '1px solid rgba(229, 210, 173, 0.4)',
                }}
              >
                {renderInlineSpans(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((rowStr, rIdx) => {
            const cells = parseRowCells(rowStr);
            const rowBg = rIdx % 2 === 0 ? '#FFFFFF' : 'rgba(248, 244, 236, 0.45)';
            return (
              <tr
                key={rIdx}
                style={{
                  background: rowBg,
                  borderBottom: rIdx === dataRows.length - 1 ? 'none' : '1px solid var(--border-subtle, #EBE1D0)',
                }}
              >
                {Array.from({ length: numCols }).map((_, cIdx) => (
                  <td
                    key={cIdx}
                    style={{
                      padding: '8px 12px',
                      color: 'var(--text-dark, #2A2020)',
                      textAlign: alignments[cIdx] || 'left',
                      fontSize: '0.83rem',
                      borderRight: cIdx === numCols - 1 ? 'none' : '1px solid rgba(235, 225, 208, 0.4)',
                    }}
                  >
                    {renderInlineSpans(cells[cIdx] || '')}
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
        border: '1px solid var(--gold-border, #E5D2AD)',
        background: '#2D050B',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '4px 10px',
          background: '#1A0307',
          color: '#E5D2AD',
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
          color: '#F5ECDA',
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

/**
 * Tokenizes inline formatting: `code`, **bold**, *italic*, [links](url)
 */
function renderInlineSpans(text) {
  if (!text) return null;

  // Regex to match code, strong, italic, links
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Inline code `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={idx}
          style={{
            background: 'rgba(184, 134, 11, 0.12)',
            padding: '1px 5px',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '0.86em',
            color: 'var(--burgundy, #58111A)',
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold **text**
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={idx} style={{ color: 'var(--burgundy, #58111A)', fontWeight: 700 }}>
          {renderInlineSpans(part.slice(2, -2))}
        </strong>
      );
    }

    // Italic *text*
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }

    // Link [label](url) - Sanitized against javascript: and malicious schemes
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const rawHref = (linkMatch[2] || '').trim();
      const isSafe = /^(https?:|mailto:|tel:)/i.test(rawHref);
      const safeHref = isSafe ? rawHref : '#';
      return (
        <a
          key={idx}
          href={safeHref}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--gold-primary, #B8860B)',
            textDecoration: 'underline',
            fontWeight: 600,
          }}
        >
          {linkMatch[1]}
        </a>
      );
    }

    return part;
  });
}
