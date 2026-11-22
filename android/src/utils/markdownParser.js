/**
 * android/src/utils/markdownParser.js
 * Pure AST-like Markdown parser for Yatra AI Android.
 * Supports GFM pipe tables, code blocks, headings, lists, horizontal rules, and paragraphs.
 * Completely decoupled from React Native UI for 100% automated testability.
 */

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

    // 2. Headings (# through ######)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      continue;
    }

    // 3. Horizontal Rule
    if (/^(---|___|\*\*\*)$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      continue;
    }

    // 4. Tables (| col1 | col2 |)
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
          /^(---|___|\*\*\*)$/.test(rowTrimmed)
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

    // 5. Bullet items (- or * or • or +)
    if (/^[-*•+]\s+/.test(trimmed)) {
      blocks.push({ type: 'bullet', text: trimmed.replace(/^[-*•+]\s+/, '') });
      continue;
    }

    // 6. Numbered items (1. or 1) )
    const numMatch = trimmed.match(/^(\d+)[\.\)]\s+(.*)/);
    if (numMatch) {
      blocks.push({ type: 'numbered', num: numMatch[1], text: numMatch[2] });
      continue;
    }

    // 7. Standard Paragraph
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
};
