import React from 'react';

/**
 * Pure JS Markdown parser for Yatra AI.
 * Uses React.createElement so it can be tested directly in Node.js
 * and bundled cleanly by Vite without transpiler mismatches.
 */

/**
 * Completes unclosed streaming markdown delimiters at the end of content
 * so partial tokens don't display raw syntax while streaming.
 */
export function completeIncompleteStreamingTokens(text) {
  if (!text) return text;

  let s = text;

  // Unclosed inline code `...
  const backtickCount = (s.match(/`/g) || []).length;
  if (backtickCount % 2 !== 0) {
    s += '`';
  }

  // Unclosed bold **...
  const doubleAsteriskMatches = s.match(/\*\*/g) || [];
  if (doubleAsteriskMatches.length % 2 !== 0) {
    s += '**';
  }

  // Unclosed bold __...
  const doubleUnderscoreMatches = s.match(/(?<![a-zA-Z0-9])__(?!\s)/g) || [];
  const doubleUnderscoreCloseMatches = s.match(/(?<!\s)__(?![a-zA-Z0-9])/g) || [];
  if (doubleUnderscoreMatches.length > doubleUnderscoreCloseMatches.length) {
    s += '__';
  }

  return s;
}

/**
 * Checks if a row is a valid markdown table delimiter row (e.g. |---|:---:|---:|)
 */
export function isTableDelimiterRow(str) {
  if (!str || !str.includes('-')) return false;
  const content = str.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells = content.split('|');
  if (cells.length === 0) return false;
  return cells.every((cell) => /^\s*:?-+:?\s*$/.test(cell));
}

export function parseRowCells(str) {
  let content = str.trim();
  if (content.startsWith('|')) content = content.substring(1);
  if (content.endsWith('|')) content = content.substring(0, content.length - 1);
  return content.split('|').map((c) => c.trim());
}

export function getAlignments(delimiterRow) {
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

/**
 * Tokenizes inline formatting: `code`, **bold**, __bold__, *italic*, _italic_,
 * ***bold italic***, [links](url), raw URLs, and ~~strikethrough~~.
 * 
 * Safety: Uses negative lookahead and lookbehind to ensure intra-word underscores
 * (e.g. `booking_id`, `pax_count`, `session_123_abc`) and URL parameters are
 * never falsely converted to italic or bold spans.
 */
export function renderInlineSpans(text) {
  if (!text) return null;

  // 1. Protect escaped characters
  const ESC_BACKSLASH = '\uE000';
  const ESC_ASTERISK = '\uE001';
  const ESC_UNDERSCORE = '\uE002';
  const ESC_HASH = '\uE003';
  const ESC_BACKTICK = '\uE004';
  const ESC_BRACKET_L = '\uE005';
  const ESC_BRACKET_R = '\uE006';

  let s = String(text)
    .replace(/\\\\/g, ESC_BACKSLASH)
    .replace(/\\\*/g, ESC_ASTERISK)
    .replace(/\\_/g, ESC_UNDERSCORE)
    .replace(/\\#/g, ESC_HASH)
    .replace(/\\`/g, ESC_BACKTICK)
    .replace(/\\\[/g, ESC_BRACKET_L)
    .replace(/\\\]/g, ESC_BRACKET_R);

  // Streaming safety
  s = completeIncompleteStreamingTokens(s);

  const restoreEscapes = (str) => {
    if (typeof str !== 'string') return str;
    return str
      .replace(new RegExp(ESC_BACKSLASH, 'g'), '\\')
      .replace(new RegExp(ESC_ASTERISK, 'g'), '*')
      .replace(new RegExp(ESC_UNDERSCORE, 'g'), '_')
      .replace(new RegExp(ESC_HASH, 'g'), '#')
      .replace(new RegExp(ESC_BACKTICK, 'g'), '`')
      .replace(new RegExp(ESC_BRACKET_L, 'g'), '[')
      .replace(new RegExp(ESC_BRACKET_R, 'g'), ']');
  };

  // Comprehensive tokenizer regex
  const INLINE_TOKEN_REGEX = /(`[^`]+`|\[[^\]]+\]\([^\s)]+\)|https?:\/\/[^\s<]+[^<.,:;"')\]\s]|\*\*\*[^*\n]+?\*\*\*|___[^_\n]+?___|\*\*_[^*_\n]+?_\*\*|\*\*[^*\n]+?\*\*|(?<![a-zA-Z0-9])__(?:[^\s_][^_\n]*?[^\s_]|[^_\s\n])__(?![a-zA-Z0-9])|(?<!\*)\*(?!\s)[^*\n]+?(?<!\s)\*(?!\*)|(?<![a-zA-Z0-9])_(?!\s)[^_\n]+?(?<!\s)_(?![a-zA-Z0-9])|~~[^~\n]+?~~)/g;

  const parts = s.split(INLINE_TOKEN_REGEX);

  return parts.map((part, idx) => {
    if (!part) return null;

    // 1. Inline code `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return React.createElement(
        'code',
        {
          key: idx,
          style: {
            background: 'var(--soft-plum-surface, #F0E3E7)',
            padding: '1px 5px',
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '0.86em',
            color: 'var(--royal-plum, #54152D)',
            border: '1px solid var(--border-default, #E9DED6)',
          },
        },
        restoreEscapes(part.slice(1, -1))
      );
    }

    // 2. Markdown link [label](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const rawHref = (linkMatch[2] || '').trim();
      const isSafe = /^(https?:|mailto:|tel:|\/|#)/i.test(rawHref);
      const safeHref = isSafe ? rawHref : '#';
      return React.createElement(
        'a',
        {
          key: idx,
          href: safeHref,
          target: '_blank',
          rel: 'noopener noreferrer',
          style: {
            color: 'var(--royal-plum, #54152D)',
            textDecoration: 'underline',
            textUnderlineOffset: '2px',
            fontWeight: 600,
          },
        },
        renderInlineSpans(linkMatch[1])
      );
    }

    // 3. Raw URL https://...
    if (/^https?:\/\//i.test(part)) {
      return React.createElement(
        'a',
        {
          key: idx,
          href: part,
          target: '_blank',
          rel: 'noopener noreferrer',
          style: {
            color: 'var(--royal-plum, #54152D)',
            textDecoration: 'underline',
            textUnderlineOffset: '2px',
            fontWeight: 600,
            wordBreak: 'break-all',
          },
        },
        restoreEscapes(part)
      );
    }

    // 4. Bold + Italic (***text*** or ___text___ or **_text_**)
    if (
      (part.startsWith('***') && part.endsWith('***') && part.length > 6) ||
      (part.startsWith('___') && part.endsWith('___') && part.length > 6) ||
      (part.startsWith('**_') && part.endsWith('_**') && part.length > 6)
    ) {
      const inner = part.slice(3, -3);
      return React.createElement(
        'strong',
        { key: idx, style: { color: 'var(--royal-plum, #54152D)', fontWeight: 800 } },
        React.createElement('em', null, renderInlineSpans(inner))
      );
    }

    // 5. Bold (**text** or __text__)
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length > 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length > 4)
    ) {
      const inner = part.slice(2, -2);
      return React.createElement(
        'strong',
        { key: idx, style: { color: 'var(--royal-plum, #54152D)', fontWeight: 700 } },
        renderInlineSpans(inner)
      );
    }

    // 6. Italic (*text* or _text_)
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length > 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length > 2)
    ) {
      const inner = part.slice(1, -1);
      return React.createElement('em', { key: idx }, renderInlineSpans(inner));
    }

    // 7. Strikethrough (~~text~~)
    if (part.startsWith('~~') && part.endsWith('~~') && part.length > 4) {
      return React.createElement('del', { key: idx }, renderInlineSpans(part.slice(2, -2)));
    }

    // 8. Plain text node
    return restoreEscapes(part);
  });
}

/**
 * Parses raw markdown text into React elements using React.createElement.
 */
export function parseMarkdownToElements(rawText, CodeBlockComponent = null, TableComponent = null) {
  if (!rawText) return [];

  const lines = String(rawText).split('\n');
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
      if (CodeBlockComponent) {
        elements.push(
          React.createElement(CodeBlockComponent, {
            key: `code-${index++}`,
            code: codeLines.join('\n'),
            language: lang,
          })
        );
      } else {
        elements.push(
          React.createElement(
            'pre',
            {
              key: `code-${index++}`,
              style: {
                background: '#200810',
                color: '#F7F1EB',
                padding: '10px 12px',
                borderRadius: '8px',
                overflowX: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.82rem',
              },
            },
            React.createElement('code', null, codeLines.join('\n'))
          )
        );
      }
      continue;
    }

    // 3. Horizontal Rule (---, ___, ***)
    if (/^(---|___|\*\*\*)\s*$/.test(trimmed)) {
      elements.push(
        React.createElement('hr', {
          key: `hr-${index++}`,
          style: {
            border: 'none',
            borderTop: '1px solid var(--border-default, #E9DED6)',
            margin: '1rem 0',
          },
        })
      );
      continue;
    }

    // 4. Headings: H1 through H6 (# to ######)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+?)(?:\s+#+)?$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2].trim();

      const headingStyles = {
        1: { fontSize: '1.28rem', fontWeight: 800, margin: '1.2rem 0 0.5rem', lineHeight: 1.3, color: 'var(--royal-plum, #54152D)' },
        2: { fontSize: '1.15rem', fontWeight: 800, margin: '1.05rem 0 0.45rem', lineHeight: 1.3, color: 'var(--royal-plum, #54152D)' },
        3: { fontSize: '1.04rem', fontWeight: 700, margin: '0.9rem 0 0.35rem', lineHeight: 1.32, color: 'var(--royal-plum, #54152D)' },
        4: { fontSize: '0.96rem', fontWeight: 700, margin: '0.8rem 0 0.3rem', lineHeight: 1.35, color: 'var(--royal-plum, #54152D)' },
        5: { fontSize: '0.90rem', fontWeight: 700, margin: '0.7rem 0 0.25rem', lineHeight: 1.35, color: 'var(--royal-plum, #54152D)' },
        6: { fontSize: '0.84rem', fontWeight: 600, margin: '0.6rem 0 0.2rem', lineHeight: 1.35, color: 'var(--champagne-taupe, #A3826C)' },
      };

      const style = {
        fontFamily: 'var(--font-serif, Cinzel, serif)',
        letterSpacing: '0.01em',
        ...headingStyles[level],
      };

      const tag = `h${Math.min(level, 6)}`;
      elements.push(
        React.createElement(tag, { key: `h-${level}-${index++}`, style }, renderInlineSpans(headingText))
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
        React.createElement(
          'blockquote',
          {
            key: `quote-${index++}`,
            style: {
              borderLeft: '3px solid var(--champagne-taupe, #A3826C)',
              background: 'var(--secondary-bg, #F2EAE4)',
              margin: '0.75rem 0',
              padding: '0.55rem 0.95rem',
              borderRadius: '0 8px 8px 0',
              fontStyle: 'italic',
              color: 'var(--royal-plum, #54152D)',
            },
          },
          quoteLines.map((ql, qIdx) =>
            React.createElement('p', { key: qIdx, style: { margin: qIdx > 0 ? '0.35rem 0 0' : 0, lineHeight: 1.5 } }, renderInlineSpans(ql))
          )
        )
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
        if (curLine.startsWith('#') || curLine.startsWith('```') || /^(---|___|\*\*\*)\s*$/.test(curLine)) {
          break;
        }
        dataRows.push(curLine);
        i++;
      }
      i--; // adjust loop counter

      if (TableComponent) {
        elements.push(
          React.createElement(TableComponent, {
            key: `table-${index++}`,
            headerRow,
            delimiterRow,
            dataRows,
          })
        );
      } else {
        const headers = parseRowCells(headerRow);
        const alignments = getAlignments(delimiterRow);
        elements.push(
          React.createElement(
            'div',
            { key: `table-${index++}`, style: { overflowX: 'auto', margin: '0.75rem 0' } },
            React.createElement(
              'table',
              { style: { width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' } },
              React.createElement(
                'thead',
                null,
                React.createElement(
                  'tr',
                  null,
                  headers.map((h, hIdx) =>
                    React.createElement(
                      'th',
                      { key: hIdx, style: { padding: '8px', textAlign: alignments[hIdx] || 'left', borderBottom: '2px solid #E9DED6' } },
                      renderInlineSpans(h)
                    )
                  )
                )
              ),
              React.createElement(
                'tbody',
                null,
                dataRows.map((rStr, rIdx) => {
                  const cells = parseRowCells(rStr);
                  return React.createElement(
                    'tr',
                    { key: rIdx, style: { borderBottom: '1px solid #E9DED6' } },
                    cells.map((c, cIdx) =>
                      React.createElement(
                        'td',
                        { key: cIdx, style: { padding: '7px 8px', textAlign: alignments[cIdx] || 'left' } },
                        renderInlineSpans(c)
                      )
                    )
                  );
                })
              )
            )
          )
        );
      }
      continue;
    }

    // 7. Unordered Lists (bullet markers: - , * , + , •)
    const ulMatch = trimmed.match(/^([•\-*+])\s+(.+)$/);
    if (ulMatch) {
      const listItems = [ulMatch[2]];
      while (i + 1 < lines.length) {
        const nextTrimmed = lines[i + 1].trim();
        const nextUlMatch = nextTrimmed.match(/^([•\-*+])\s+(.+)$/);
        if (nextUlMatch) {
          listItems.push(nextUlMatch[2]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        React.createElement(
          'ul',
          {
            key: `ul-${index++}`,
            style: {
              margin: '0.45rem 0 0.75rem 1.35rem',
              paddingLeft: 0,
              listStyleType: 'disc',
            },
          },
          listItems.map((item, liIdx) =>
            React.createElement('li', { key: liIdx, style: { margin: '0.25rem 0', lineHeight: 1.52 } }, renderInlineSpans(item))
          )
        )
      );
      continue;
    }

    // 8. Ordered Lists (1. ... or 1) ...)
    const olMatch = trimmed.match(/^(\d+)[.)]\s+(.+)$/);
    if (olMatch) {
      const listItems = [olMatch[2]];
      while (i + 1 < lines.length) {
        const nextTrimmed = lines[i + 1].trim();
        const nextOlMatch = nextTrimmed.match(/^(\d+)[.)]\s+(.+)$/);
        if (nextOlMatch) {
          listItems.push(nextOlMatch[2]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        React.createElement(
          'ol',
          {
            key: `ol-${index++}`,
            style: {
              margin: '0.45rem 0 0.75rem 1.35rem',
              paddingLeft: 0,
            },
          },
          listItems.map((item, liIdx) =>
            React.createElement('li', { key: liIdx, style: { margin: '0.25rem 0', lineHeight: 1.52 } }, renderInlineSpans(item))
          )
        )
      );
      continue;
    }

    // 9. Standard Paragraph
    elements.push(
      React.createElement(
        'p',
        { key: `p-${index++}`, style: { margin: '0 0 0.65rem 0', lineHeight: 1.6 } },
        renderInlineSpans(trimmed)
      )
    );
  }

  return elements;
}

