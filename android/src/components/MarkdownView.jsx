import React from 'react';
import { View, Text, StyleSheet, Linking, ScrollView } from 'react-native';
import { colors } from '../theme/colors';
import {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
  completeIncompleteStreamingTokens,
} from '../utils/markdownParser';

// Re-export parser utilities for backwards compatibility
export {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
  completeIncompleteStreamingTokens,
};

/**
 * Mobile-optimized Markdown Table Component
 * Features:
 * - Sacred Burgundy header row (#58111A) with white typography
 * - Alternating warm ivory (#F8F4EC) and white (#FFFFFF) rows
 * - Subtle temple gold border (#E5D2AD)
 * - Horizontal swipe/scroll for wide tables without bubble overflow
 * - Proper cell padding and multiline text wrapping
 */
function MarkdownTable({ headers, alignments, dataRows, columnWidths, numCols, textColor }) {
  const totalWidth = columnWidths.reduce((sum, w) => sum + w, 0);
  const isWideTable = totalWidth > 280;

  return (
    <View style={styles.tableCard}>
      {isWideTable && (
        <View style={styles.scrollHintBar}>
          <Text style={styles.scrollHintText}>↔ Swipe horizontally to view full table</Text>
        </View>
      )}
      <ScrollView
        horizontal={true}
        showsHorizontalScrollIndicator={true}
        nestedScrollEnabled={true}
        contentContainerStyle={[styles.tableScrollContent, { minWidth: '100%' }]}
      >
        <View style={[styles.tableContainer, { minWidth: Math.max(totalWidth, 260) }]}>
          {/* Header Row */}
          <View style={styles.tableHeaderRow}>
            {headers.map((h, colIdx) => {
              const align = alignments[colIdx] || 'left';
              const isLast = colIdx === numCols - 1;
              return (
                <View
                  key={`th-${colIdx}`}
                  style={[
                    styles.thCell,
                    {
                      width: columnWidths[colIdx],
                      alignItems:
                        align === 'center'
                          ? 'center'
                          : align === 'right'
                          ? 'flex-end'
                          : 'flex-start',
                      borderRightWidth: isLast ? 0 : 1,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.thText,
                      {
                        textAlign: align,
                      },
                    ]}
                  >
                    {renderInlineSpans(h, colors.textWhite || '#FFFFFF')}
                  </Text>
                </View>
              );
            })}
          </View>

          {/* Data Rows */}
          {dataRows.map((cells, rowIdx) => {
            const isEven = rowIdx % 2 === 0;
            const isLastRow = rowIdx === dataRows.length - 1;
            return (
              <View
                key={`tr-${rowIdx}`}
                style={[
                  styles.tableDataRow,
                  isEven ? styles.tableRowEven : styles.tableRowOdd,
                  isLastRow && { borderBottomWidth: 0 },
                ]}
              >
                {Array.from({ length: numCols }).map((_, colIdx) => {
                  const cellText = cells[colIdx] || '';
                  const align = alignments[colIdx] || 'left';
                  const isLastCol = colIdx === numCols - 1;
                  return (
                    <View
                      key={`td-${rowIdx}-${colIdx}`}
                      style={[
                        styles.tdCell,
                        {
                          width: columnWidths[colIdx],
                          alignItems:
                            align === 'center'
                              ? 'center'
                              : align === 'right'
                              ? 'flex-end'
                              : 'flex-start',
                          borderRightWidth: isLastCol ? 0 : 1,
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.tdText,
                          {
                            color: textColor,
                            textAlign: align,
                          },
                        ]}
                      >
                        {renderInlineSpans(cellText, textColor)}
                      </Text>
                    </View>
                  );
                })}
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

function MarkdownView({ content = '', textColor = colors.textPrimary }) {
  if (!content || typeof content !== 'string') return null;

  try {
    // Complete any dangling streaming tokens before parsing structure
    const safeContent = completeIncompleteStreamingTokens(content);
    const blocks = parseMarkdownStructure(safeContent);

    return (
      <View style={styles.container}>
        {blocks.map((block, idx) => {
          try {
            switch (block.type) {
              case 'empty':
                return <View key={`empty-${idx}`} style={{ height: 6 }} />;

              case 'code':
                return (
                  <View key={`code-${idx}`} style={styles.codeBlock}>
                    <Text style={styles.codeBlockText}>{block.code}</Text>
                  </View>
                );

              case 'heading': {
                const hStyle =
                  block.level === 1
                    ? styles.h1
                    : block.level === 2
                    ? styles.h2
                    : block.level === 3
                    ? styles.h3
                    : block.level === 4
                    ? styles.h4
                    : block.level === 5
                    ? styles.h5
                    : styles.h6;
                const headingColor =
                  block.level === 6
                    ? colors.champagneTaupe || '#A3826C'
                    : colors.royalPlum || '#54152D';
                return (
                  <Text key={`h-${idx}`} style={[hStyle, { color: headingColor }]}>
                    {renderInlineSpans(block.text, headingColor)}
                  </Text>
                );
              }

              case 'quote':
                return (
                  <View key={`quote-${idx}`} style={styles.quoteBlock}>
                    <Text style={styles.quoteText}>
                      {renderInlineSpans(block.text, colors.royalPlum || '#54152D')}
                    </Text>
                  </View>
                );

              case 'hr':
                return <View key={`hr-${idx}`} style={styles.hr} />;

              case 'table':
                return (
                  <MarkdownTable
                    key={`tbl-${idx}`}
                    headers={block.headers}
                    alignments={block.alignments}
                    dataRows={block.dataRows}
                    columnWidths={block.columnWidths}
                    numCols={block.numCols}
                    textColor={textColor}
                  />
                );

              case 'bullet':
                return (
                  <View key={`bullet-${idx}`} style={styles.bulletRow}>
                    <Text style={styles.bulletDot}>•</Text>
                    <Text style={[styles.bulletText, { color: textColor }]}>
                      {renderInlineSpans(block.text, textColor)}
                    </Text>
                  </View>
                );

              case 'numbered':
                return (
                  <View key={`num-${idx}`} style={styles.bulletRow}>
                    <Text style={styles.numDot}>{block.num}.</Text>
                    <Text style={[styles.bulletText, { color: textColor }]}>
                      {renderInlineSpans(block.text, textColor)}
                    </Text>
                  </View>
                );

              case 'paragraph':
              default:
                return (
                  <Text key={`p-${idx}`} style={[styles.paragraph, { color: textColor }]}>
                    {renderInlineSpans(block.text, textColor)}
                  </Text>
                );
            }
          } catch {
            return (
              <Text key={`fallback-${idx}`} style={[styles.paragraph, { color: textColor }]}>
                {block.text || ''}
              </Text>
            );
          }
        })}
      </View>
    );
  } catch {
    return (
      <View style={styles.container}>
        <Text style={[styles.paragraph, { color: textColor }]}>{content}</Text>
      </View>
    );
  }
}

export default React.memo(MarkdownView);

/**
 * Tokenizes bold, italic, inline code, strikethrough, and sanitized links.
 *
 * Identifier safety: Uses negative lookahead and lookbehind so intra-word underscores
 * (e.g. `booking_id`, `pax_count`, `session_123_abc`) and URL parameters are never
 * converted to italic or bold spans.
 */
export function renderInlineSpans(text, defaultColor = colors.textPrimary, depth = 0) {
  if (!text) return null;
  if (depth > 2) {
    return <Text style={{ color: defaultColor }}>{String(text)}</Text>;
  }

  try {
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

    // Complete any trailing incomplete token
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
        return (
          <Text key={idx} style={styles.inlineCode}>
            {restoreEscapes(part.slice(1, -1))}
          </Text>
        );
      }

      // 2. Markdown link [label](url)
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        const rawUrl = (linkMatch[2] || '').trim();
        const isSafe = /^(https?:|mailto:|tel:)/i.test(rawUrl);
        if (!isSafe) {
          return (
            <Text key={idx} style={{ color: defaultColor }}>
              {renderInlineSpans(linkMatch[1], defaultColor, depth + 1)}
            </Text>
          );
        }
        return (
          <Text
            key={idx}
            style={styles.link}
            onPress={() => Linking.openURL(rawUrl).catch(() => {})}
          >
            {renderInlineSpans(linkMatch[1], colors.royalPlum || '#54152D', depth + 1)}
          </Text>
        );
      }

      // 3. Raw URL https://... (preserving underscores and hashes)
      if (/^https?:\/\//i.test(part)) {
        const cleanUrl = restoreEscapes(part);
        return (
          <Text
            key={idx}
            style={styles.link}
            onPress={() => Linking.openURL(cleanUrl).catch(() => {})}
          >
            {cleanUrl}
          </Text>
        );
      }

      // 4. Bold + Italic (***text*** or ___text___ or **_text_**)
      if (
        (part.startsWith('***') && part.endsWith('***') && part.length > 6) ||
        (part.startsWith('___') && part.endsWith('___') && part.length > 6) ||
        (part.startsWith('**_') && part.endsWith('_**') && part.length > 6)
      ) {
        const inner = part.slice(3, -3);
        return (
          <Text key={idx} style={[styles.bold, styles.italic, { color: colors.royalPlum || '#54152D' }]}>
            {renderInlineSpans(inner, colors.royalPlum || '#54152D', depth + 1)}
          </Text>
        );
      }

      // 5. Bold (**text** or __text__)
      if (
        (part.startsWith('**') && part.endsWith('**') && part.length > 4) ||
        (part.startsWith('__') && part.endsWith('__') && part.length > 4)
      ) {
        const inner = part.slice(2, -2);
        return (
          <Text key={idx} style={[styles.bold, { color: colors.royalPlum || '#54152D' }]}>
            {renderInlineSpans(inner, colors.royalPlum || '#54152D', depth + 1)}
          </Text>
        );
      }

      // 6. Italic (*text* or _text_)
      if (
        (part.startsWith('*') && part.endsWith('*') && part.length > 2) ||
        (part.startsWith('_') && part.endsWith('_') && part.length > 2)
      ) {
        const inner = part.slice(1, -1);
        return (
          <Text key={idx} style={[styles.italic, { color: defaultColor }]}>
            {renderInlineSpans(inner, defaultColor, depth + 1)}
          </Text>
        );
      }

      // 7. Strikethrough (~~text~~)
      if (part.startsWith('~~') && part.endsWith('~~') && part.length > 4) {
        const inner = part.slice(2, -2);
        return (
          <Text key={idx} style={styles.strikethrough}>
            {renderInlineSpans(inner, defaultColor, depth + 1)}
          </Text>
        );
      }

      // 8. Plain text node
      return <Text key={idx}>{restoreEscapes(part)}</Text>;
    });
  } catch {
    return <Text style={{ color: defaultColor }}>{String(text)}</Text>;
  }
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  paragraph: {
    fontSize: 14.5,
    lineHeight: 22,
    marginBottom: 6,
  },
  h1: {
    fontSize: 19,
    fontWeight: '800',
    marginBottom: 6,
    marginTop: 6,
    letterSpacing: 0.2,
  },
  h2: {
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 5,
    marginTop: 5,
    letterSpacing: 0.2,
  },
  h3: {
    fontSize: 15.5,
    fontWeight: '700',
    marginBottom: 4,
    marginTop: 3,
  },
  h4: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 3,
    marginTop: 2,
  },
  h5: {
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 3,
    marginTop: 2,
  },
  h6: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 2,
    marginTop: 2,
    letterSpacing: 0.3,
  },
  bold: {
    fontWeight: '700',
  },
  italic: {
    fontStyle: 'italic',
  },
  strikethrough: {
    textDecorationLine: 'line-through',
    color: colors.textMuted || '#A39994',
  },
  inlineCode: {
    fontFamily: 'monospace',
    backgroundColor: 'rgba(84, 21, 45, 0.08)',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
    fontSize: 13,
    color: colors.royalPlum || '#54152D',
  },
  link: {
    color: colors.royalPlum || '#54152D',
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
  quoteBlock: {
    borderLeftWidth: 3,
    borderLeftColor: colors.champagneTaupe || '#A3826C',
    backgroundColor: colors.softPlum || '#F0E3E7',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    marginVertical: 6,
  },
  quoteText: {
    fontStyle: 'italic',
    fontSize: 13.5,
    lineHeight: 20,
  },
  codeBlock: {
    backgroundColor: '#1E0408',
    padding: 10,
    borderRadius: 8,
    marginVertical: 6,
  },
  codeBlockText: {
    color: '#F5ECDA',
    fontFamily: 'monospace',
    fontSize: 12.5,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 4,
    paddingLeft: 4,
  },
  bulletDot: {
    fontSize: 14,
    marginRight: 6,
    color: colors.champagneTaupe || '#A3826C',
    fontWeight: '800',
  },
  numDot: {
    fontSize: 13,
    fontWeight: '700',
    marginRight: 6,
    color: colors.champagneTaupe || '#A3826C',
  },
  bulletText: {
    fontSize: 14,
    lineHeight: 20,
    flex: 1,
  },
  hr: {
    height: 1,
    backgroundColor: colors.borderDefault || '#E9DED6',
    marginVertical: 8,
  },

  // Table styles
  tableCard: {
    marginVertical: 8,
    borderRadius: 8,
    borderWidth: 1.2,
    borderColor: colors.goldBorder || '#E5D2AD',
    backgroundColor: colors.surfaceWhite || '#FFFFFF',
    overflow: 'hidden',
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  scrollHintBar: {
    backgroundColor: 'rgba(163, 130, 108, 0.1)',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle || '#F5ECE6',
    paddingVertical: 3.5,
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollHintText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: colors.champagneTaupe || '#A3826C',
    letterSpacing: 0.3,
  },
  tableScrollContent: {
    flexGrow: 0,
  },
  tableContainer: {
    flexDirection: 'column',
  },
  tableHeaderRow: {
    flexDirection: 'row',
    backgroundColor: colors.burgundy || '#54152D',
    borderBottomWidth: 2,
    borderBottomColor: colors.champagneTaupe || '#A3826C',
  },
  thCell: {
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderRightColor: 'rgba(247, 241, 235, 0.25)',
    justifyContent: 'center',
  },
  thText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  tableDataRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle || '#F5ECE6',
  },
  tableRowEven: {
    backgroundColor: '#FFFFFF',
  },
  tableRowOdd: {
    backgroundColor: colors.softPlum || '#FBF8F5',
  },
  tdCell: {
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRightColor: 'rgba(233, 222, 214, 0.45)',
    justifyContent: 'center',
  },
  tdText: {
    fontSize: 12,
    lineHeight: 16,
  },
});
