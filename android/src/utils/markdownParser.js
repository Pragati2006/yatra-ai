/**
 * android/src/utils/markdownParser.js
 * Pure AST-like Markdown parser for Yatra AI Android.
 * Supports GFM pipe tables, code blocks, headings (H1-H6), blockquotes,
 * lists (ordered and unordered), horizontal rules, and paragraphs.
 * Completely decoupled from React Native UI for 100% automated testability.
 */

/**
 * Completes unclosed streaming markdown delimiters at the end of content
 * so partial tokens don't display raw dangling delimiters while streaming.
 */
export function completeIncompleteStreamingTokens(text) {
  if (!text || typeof text !== 'string') return text || '';

  let s = text;

  // 1. Unclosed inline code `...
  const backtickCount = (s.match(/`/g) || []).length;
  if (backtickCount % 2 !== 0) {
    s += '`';
  }

  // 2. Unclosed bold **...
  const doubleAsteriskMatches = s.match(/\*\*/g) || [];
  if (doubleAsteriskMatches.length % 2 !== 0) {
    s += '**';
  }

  // 3. Unclosed bold __...
  const doubleUnderscoreOpen = s.match(/(?<![a-zA-Z0-9])__(?!\s)/g) || [];
  const doubleUnderscoreClose = s.match(/(?<!\s)__(?![a-zA-Z0-9])/g) || [];
  if (doubleUnderscoreOpen.length > doubleUnderscoreClose.length) {
    s += '__';
  }

  // 4. Unclosed italic *... (not part of **)
  const singleAsteriskMatches = s.match(/(?<!\*)\*(?!\*)/g) || [];
  if (singleAsteriskMatches.length % 2 !== 0) {
    s += '*';
  }

  // 5. Unclosed italic _... (not part of intra-word identifier like booking_id)
  const singleUnderscoreOpen = s.match(/(?<![a-zA-Z0-9_])_(?![_\s])/g) || [];
  const singleUnderscoreClose = s.match(/(?<![\s_])_(?![a-zA-Z0-9_])/g) || [];
  if (singleUnderscoreOpen.length > singleUnderscoreClose.length) {
    s += '_';
  }

  // 6. Unclosed strikethrough ~~...
  const tildeMatches = s.match(/~~/g) || [];
  if (tildeMatches.length % 2 !== 0) {
    s += '~~';
  }

  return s;
}

/**
 * Checks if a string is a valid GitHub-Flavored Markdown table delimiter row.
 * E.g. |---|---| or |:---|:---:|---:| or ---|---
 */
export function isTableDelimiterRow(str) {
  if (!str || typeof str !== 'string' || !str.includes('-')) return false;
  const trimmed = str.trim();
  if (!trimmed.includes('|')) return false;
  const content = trimmed.replace(/^\|/, '').replace(/\|$/, '');
  const cells = content.split('|');
  if (cells.length === 0) return false;
  return cells.every((cell) => /^\s*:?-+:?\s*$/.test(cell));
}

/**
 * Splits a markdown table row into trimmed cell values, respecting escaped pipes \|
 */
export function parseRowCells(str) {
  if (!str || typeof str !== 'string') return [];
  let content = str.trim();
  if (content.startsWith('|')) content = content.substring(1);
  if (content.endsWith('|')) content = content.substring(0, content.length - 1);
  return content
    .replace(/\\\|/g, '__ESCAPED_PIPE__')
    .split('|')
    .map((c) => c.replace(/__ESCAPED_PIPE__/g, '|').trim());
}

/**
 * Computes text alignments per column from the markdown delimiter row
 */
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
 * Dynamically computes minimum column widths so wide multi-column tables
 * (e.g. 7-column transport matrices) breathe nicely in horizontal scroll.
 */
export function computeColumnWidths(headers, dataRows) {
  const numCols = headers.length;
  const widths = [];

  for (let c = 0; c < numCols; c++) {
    let maxChars = (headers[c] || '').length;
    for (let r = 0; r < dataRows.length; r++) {
      const cellText = dataRows[r][c] || '';
      if (cellText.length > maxChars) {
        maxChars = cellText.length;
      }
    }

    if (maxChars <= 3) {
      widths.push(48);
    } else if (maxChars <= 6) {
      widths.push(74);
    } else if (maxChars <= 10) {
      widths.push(98);
    } else if (maxChars <= 16) {
      widths.push(122);
    } else if (maxChars <= 24) {
      widths.push(148);
    } else {
      widths.push(175);
    }
  }

  return widths;
}

/**
 * Parses markdown text into an AST-like array of block tokens
 */
export function parseMarkdownStructure(content) {
  if (!content || typeof content !== 'string') return [];
  const lines = content.split('\n');
  const blocks = [];

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      blocks.push({ type: 'empty' });
      continue;
    }

    // 1. Code blocks (```language ... ```)
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: 'code', code: codeLines.join('\n'), lang });
      continue;
    }

    // 2. Headings (H1 through H6: # to ######)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+?)(?:\s+#+)?$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      continue;
    }

    // 3. Blockquotes (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines = [trimmed.replace(/^>\s?/, '')];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('>')) {
        i++;
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
      }
      blocks.push({
        type: 'quote',
        text: quoteLines.join('\n'),
      });
      continue;
    }

    // 4. Horizontal Rule
    if (/^(---|___|\*\*\*)\s*$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      continue;
    }

    // 5. Tables (| col1 | col2 |)
    if (trimmed.includes('|') && i + 1 < lines.length && isTableDelimiterRow(lines[i + 1])) {
      const headerRow = trimmed;
      const delimiterRow = lines[i + 1].trim();
      i += 2;
      const rawDataRows = [];
      while (i < lines.length) {
        const rowTrimmed = lines[i].trim();
        if (
          !rowTrimmed ||
          !rowTrimmed.includes('|') ||
          rowTrimmed.startsWith('```') ||
          rowTrimmed.startsWith('#') ||
          /^(---|___|\*\*\*)\s*$/.test(rowTrimmed)
        ) {
          break;
        }
        rawDataRows.push(rowTrimmed);
        i++;
      }
      i--; // adjust loop counter

      const headers = parseRowCells(headerRow);
      const alignments = getAlignments(delimiterRow);
      const parsedDataRows = rawDataRows.map((r) => parseRowCells(r));
      const numCols = Math.max(
        headers.length,
        alignments.length,
        ...parsedDataRows.map((r) => r.length)
      );

      while (headers.length < numCols) headers.push('');
      while (alignments.length < numCols) alignments.push('left');

      const columnWidths = computeColumnWidths(headers, parsedDataRows);

      blocks.push({
        type: 'table',
        headers,
        alignments,
        dataRows: parsedDataRows,
        columnWidths,
        numCols,
      });
      continue;
    }

    // 6. Bullet items (- or * or • or +)
    if (/^[-*•+]\s+/.test(trimmed)) {
      blocks.push({ type: 'bullet', text: trimmed.replace(/^[-*•+]\s+/, '') });
      continue;
    }

    // 7. Numbered items (1. or 1) )
    const numMatch = trimmed.match(/^(\d+)[\.\)]\s+(.*)/);
    if (numMatch) {
      blocks.push({ type: 'numbered', num: numMatch[1], text: numMatch[2] });
      continue;
    }

    // 8. Standard Paragraph
    blocks.push({ type: 'paragraph', text: trimmed });
  }

  return blocks;
}

export default {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
  completeIncompleteStreamingTokens,
};
