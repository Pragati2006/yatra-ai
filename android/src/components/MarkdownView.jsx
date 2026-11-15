import React from 'react';
import { View, Text, StyleSheet, Linking, ScrollView } from 'react-native';
import { colors } from '../theme/colors';
import {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
} from '../utils/markdownParser';

// Re-export parser utilities for backwards compatibility
export {
  isTableDelimiterRow,
  parseRowCells,
  getAlignments,
  computeColumnWidths,
  parseMarkdownStructure,
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
                    {renderInlineSpans(h, colors.textWhite)}
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

export default function MarkdownView({ content = '', textColor = colors.textPrimary }) {
  if (!content || typeof content !== 'string') return null;

  const blocks = parseMarkdownStructure(content);

  return (
    <View style={styles.container}>
      {blocks.map((block, idx) => {
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
            const hStyle = block.level === 1 ? styles.h1 : block.level === 2 ? styles.h2 : styles.h3;
            return (
              <Text key={`h-${idx}`} style={[hStyle, { color: textColor }]}>
                {renderInlineSpans(block.text, textColor)}
              </Text>
            );
          }

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
      })}
    </View>
  );
}

/**
 * Tokenizes bold, italic, inline code, and sanitized links
 */
export function renderInlineSpans(text, defaultColor) {
  if (!text) return null;

  // Regex matches `code`, **bold**, *italic*, [label](url)
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Inline code `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <Text key={idx} style={styles.inlineCode}>
          {part.slice(1, -1)}
        </Text>
      );
    }

    // Bold **text**
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <Text key={idx} style={[styles.bold, { color: defaultColor }]}>
          {renderInlineSpans(part.slice(2, -2), defaultColor)}
        </Text>
      );
    }

    // Italic *text*
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return (
        <Text key={idx} style={[styles.italic, { color: defaultColor }]}>
          {part.slice(1, -1)}
        </Text>
      );
    }

    // Link [label](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const rawUrl = (linkMatch[2] || '').trim();
      const isSafe = /^(https?:|mailto:|tel:)/i.test(rawUrl);
      if (!isSafe) {
        return <Text key={idx} style={{ color: defaultColor }}>{linkMatch[1]}</Text>;
      }
      return (
        <Text
          key={idx}
          style={styles.link}
          onPress={() => Linking.openURL(rawUrl).catch(() => {})}
        >
          {linkMatch[1]}
        </Text>
      );
    }

    return <Text key={idx}>{part}</Text>;
  });
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  paragraph: {
    fontSize: 14.5,
    lineHeight: 21,
    marginBottom: 6,
  },
  h1: {
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 6,
    marginTop: 4,
  },
  h2: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
    marginTop: 4,
  },
  h3: {
    fontSize: 14.5,
    fontWeight: '700',
    marginBottom: 4,
    marginTop: 2,
  },
  bold: {
    fontWeight: '700',
  },
  italic: {
    fontStyle: 'italic',
  },
  inlineCode: {
    fontFamily: 'monospace',
    backgroundColor: 'rgba(184, 134, 11, 0.15)',
    paddingHorizontal: 4,
    borderRadius: 3,
    fontSize: 13,
  },
  link: {
    color: colors.gold,
    textDecorationLine: 'underline',
    fontWeight: '600',
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
    color: colors.gold,
  },
  numDot: {
    fontSize: 13,
    fontWeight: '700',
    marginRight: 6,
    color: colors.gold,
  },
  bulletText: {
    fontSize: 14,
    lineHeight: 20,
    flex: 1,
  },
  hr: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 8,
  },

  // Table styles
  tableCard: {
    marginVertical: 8,
    borderRadius: 8,
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
    backgroundColor: colors.bgCard,
    overflow: 'hidden',
    shadowColor: colors.burgundy,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  scrollHintBar: {
    backgroundColor: 'rgba(184, 134, 11, 0.08)',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    paddingVertical: 3.5,
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollHintText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: colors.gold,
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
    backgroundColor: colors.burgundy,
    borderBottomWidth: 2,
    borderBottomColor: colors.gold,
  },
  thCell: {
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderRightColor: 'rgba(229, 210, 173, 0.3)',
    justifyContent: 'center',
  },
  thText: {
    color: colors.textWhite,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  tableDataRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  tableRowEven: {
    backgroundColor: '#FFFFFF',
  },
  tableRowOdd: {
    backgroundColor: colors.bgSubtle,
  },
  tdCell: {
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRightColor: 'rgba(232, 222, 201, 0.45)',
    justifyContent: 'center',
  },
  tdText: {
    fontSize: 12,
    lineHeight: 16,
  },
});
