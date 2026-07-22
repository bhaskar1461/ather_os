/**
 * Visual Report Renderer — Parses and renders the structured AI astrology report JSON in the mobile app.
 *
 * Simulates the web client's VisualReportRenderer with premium React Native elements,
 * custom markdown string parsing (nested <Text> components), and celestial aesthetics.
 */

import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { colors, fonts, fontSizes, spacing, radii } from '../../theme/tokens';

interface Metric {
  label: string;
  value: string;
  rating?: string;
}

interface Component {
  type: string;
  heading?: string;
  content: string;
  metadata?: Record<string, any>;
}

interface Section {
  id: string;
  title: string;
  components: Component[];
}

interface ReportData {
  report_title: string;
  subtitle: string;
  executive_summary?: {
    metrics: Metric[];
    overall_score?: number;
  };
  sections: Section[];
}

interface VisualReportRendererProps {
  json: string;
}

// ── Simple Inline Markdown Parser to React Native Elements ──────────────────

function parseBoldAndItalic(text: string, baseStyle: object = {}): React.ReactNode[] {
  if (!text) return [];

  // Parse `code`, **bold**, *italic*
  const tokenRegex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <Text key={index} style={[styles.boldText, baseStyle]}>
          {part.slice(2, -2)}
        </Text>
      );
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return (
        <Text key={index} style={[styles.italicText, baseStyle]}>
          {part.slice(1, -1)}
        </Text>
      );
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <Text key={index} style={[styles.codeText, baseStyle]}>
          {part.slice(1, -1)}
        </Text>
      );
    }
    return <Text key={index} style={baseStyle}>{part}</Text>;
  });
}

// ── Robust Stream JSON Parser ────────────────────────────────────────────────

function parsePartialJSON(jsonString: string): ReportData | null {
  let cleanStr = jsonString.trim();
  if (!cleanStr) return null;

  // Strip markdown code block wrappers (e.g. ```json ... ```)
  if (cleanStr.startsWith('```')) {
    cleanStr = cleanStr.replace(/^```(?:json)?\n?/, '').replace(/```$/, '').trim();
  }

  try {
    return JSON.parse(cleanStr);
  } catch (e) {
    let temp = cleanStr;

    // Handle trailing comma
    if (temp.endsWith(',')) {
      temp = temp.slice(0, -1);
    }

    // Balance unclosed quotes
    const quoteCount = (temp.match(/"/g) || []).length;
    if (quoteCount % 2 !== 0) {
      temp += '"';
    }

    // Walk string to identify open brackets and braces
    const openTags: string[] = [];
    let insideString = false;
    for (let i = 0; i < temp.length; i++) {
      if (temp[i] === '"' && temp[i - 1] !== '\\') {
        insideString = !insideString;
      }
      if (!insideString) {
        if (temp[i] === '{' || temp[i] === '[') {
          openTags.push(temp[i]);
        } else if (temp[i] === '}') {
          if (openTags[openTags.length - 1] === '{') openTags.pop();
        } else if (temp[i] === ']') {
          if (openTags[openTags.length - 1] === '[') openTags.pop();
        }
      }
    }

    // Append closures in reverse order
    while (openTags.length > 0) {
      const tag = openTags.pop();
      if (tag === '{') temp += '}';
      if (tag === '[') temp += ']';
    }

    try {
      return JSON.parse(temp);
    } catch (innerError) {
      return null;
    }
  }
}

export default function VisualReportRenderer({ json }: VisualReportRendererProps) {
  const lastValidData = useRef<ReportData | null>(null);
  const data = parsePartialJSON(json);

  if (data) {
    lastValidData.current = data;
  }

  const renderData = data || lastValidData.current;

  if (!renderData) {
    return (
      <View style={styles.decodingContainer}>
        <ActivityIndicator size="large" color={colors.accent.indigo} />
        <Text style={styles.decodingText}>Channelling cosmic blueprint…</Text>
      </View>
    );
  }

  // Get icons based on metric labels
  const getMetricIcon = (label: string) => {
    const lower = label.toLowerCase();
    if (lower.includes('vitality') || lower.includes('self') || lower.includes('health')) return '⚡';
    if (lower.includes('peace') || lower.includes('mind')) return '🧭';
    if (lower.includes('career') || lower.includes('karma')) return '💼';
    if (lower.includes('wealth') || lower.includes('finance')) return '🪙';
    if (lower.includes('love') || lower.includes('relationship')) return '💖';
    if (lower.includes('spiritual') || lower.includes('dharma')) return '🏆';
    return '✦';
  };

  return (
    <View style={styles.container}>
      {/* Title block */}
      <View style={styles.titleBlock}>
        <View style={styles.badgeContainer}>
          <Text style={styles.badgeText}>✦ VEDIC ASTROLOGY BLUEPRINT ✦</Text>
        </View>
        <Text style={styles.reportTitle}>{renderData.report_title}</Text>
        {renderData.subtitle && (
          <Text style={styles.reportSubtitle}>{renderData.subtitle}</Text>
        )}
      </View>

      {/* Executive Summary */}
      {renderData.executive_summary && (
        <View style={styles.summaryCard}>
          <View style={styles.summaryHeader}>
            <Text style={styles.summaryHeaderIcon}>🧭</Text>
            <Text style={styles.summaryHeaderText}>EXECUTIVE SUMMARY</Text>
            {renderData.executive_summary.overall_score && (
              <View style={styles.overallScoreBadge}>
                <Text style={styles.overallScoreText}>
                  Score: {renderData.executive_summary.overall_score}
                </Text>
              </View>
            )}
          </View>

          <View style={styles.metricsGrid}>
            {renderData.executive_summary.metrics &&
              Array.isArray(renderData.executive_summary.metrics) &&
              renderData.executive_summary.metrics.map((m, idx) => (
                <View key={idx} style={styles.metricRow}>
                  <View style={styles.metricLabelContainer}>
                    <Text style={styles.metricEmoji}>{getMetricIcon(m.label)}</Text>
                    <Text style={styles.metricLabel}>{m.label}</Text>
                  </View>
                  <View style={styles.metricValueContainer}>
                    <Text style={styles.metricValue}>{m.value}</Text>
                    {m.rating && (
                      <View
                        style={[
                          styles.ratingBadge,
                          m.rating.includes('🟢') || m.rating.toLowerCase().includes('favorable')
                            ? styles.ratingFavorable
                            : m.rating.includes('🟡') || m.rating.toLowerCase().includes('mixed')
                            ? styles.ratingMixed
                            : styles.ratingChallenging,
                        ]}
                      >
                        <Text style={styles.ratingText}>
                          {m.rating.replace(/[🟢🟡🔴]\s*/g, '')}
                        </Text>
                      </View>
                    )}
                  </View>
                </View>
              ))}
          </View>
        </View>
      )}

      {/* Report Sections */}
      {renderData.sections &&
        renderData.sections.map((section) => (
          <View key={section.id} style={styles.sectionContainer}>
            <View style={styles.sectionHeader}>
              <View style={styles.sectionIndicator} />
              <Text style={styles.sectionTitle}>{section.title}</Text>
            </View>

            <View style={styles.componentsContainer}>
              {section.components &&
                section.components.map((comp, idx) => {
                  const content = comp.content || '';
                  switch (comp.type) {
                    case 'card':
                      return (
                        <View key={idx} style={styles.componentCard}>
                          {comp.heading && (
                            <Text style={styles.componentHeading}>
                              {comp.heading.startsWith('✨') ? comp.heading : `✨ ${comp.heading}`}
                            </Text>
                          )}
                          <Text style={styles.componentBody}>
                            {parseBoldAndItalic(content, styles.componentText)}
                          </Text>
                        </View>
                      );

                    case 'callout':
                      return (
                        <View key={idx} style={styles.componentCallout}>
                          <View style={styles.calloutAccent} />
                          <View style={styles.calloutContent}>
                            {comp.heading && (
                              <Text style={styles.calloutHeading}>{comp.heading}</Text>
                            )}
                            <Text style={styles.calloutBody}>
                              {parseBoldAndItalic(content, styles.calloutText)}
                            </Text>
                          </View>
                        </View>
                      );

                    case 'table':
                      return (
                        <View key={idx} style={styles.tableContainer}>
                          {comp.heading && (
                            <Text style={styles.tableHeading}>📊 {comp.heading}</Text>
                          )}
                          <View style={styles.tableCard}>
                            {content
                              .split('\n')
                              .filter((line) => line.includes('|'))
                              .map((line, rIdx) => {
                                const cells = line
                                  .split('|')
                                  .map((c) => c.trim())
                                  .filter((_, cIdx, arr) => cIdx > 0 && cIdx < arr.length - 1);
                                if (line.includes('---')) return null;

                                const isHeader = rIdx === 0;
                                return (
                                  <View
                                    key={rIdx}
                                    style={[
                                      styles.tableRow,
                                      isHeader ? styles.tableHeaderRow : styles.tableBodyRow,
                                    ]}
                                  >
                                    {cells.map((cell, cIdx) => (
                                      <Text
                                        key={cIdx}
                                        style={[
                                          styles.tableCell,
                                          isHeader ? styles.tableHeaderCell : styles.tableBodyCell,
                                        ]}
                                      >
                                        {parseBoldAndItalic(cell, isHeader ? styles.tableHeaderCell : styles.tableBodyCell)}
                                      </Text>
                                    ))}
                                  </View>
                                );
                              })}
                          </View>
                        </View>
                      );

                    case 'list':
                      return (
                        <View key={idx} style={styles.listContainer}>
                          {comp.heading && (
                            <Text style={styles.listHeading}>{comp.heading}</Text>
                          )}
                          <View style={styles.listCard}>
                            {content
                              .split('\n')
                              .filter(
                                (l) =>
                                  l.trim().startsWith('-') ||
                                  l.trim().startsWith('✅') ||
                                  l.trim().startsWith('⚠') ||
                                  l.trim().startsWith('❌')
                              )
                              .map((item, iIdx) => {
                                const isCheck = item.includes('✅');
                                const isWarning = item.includes('⚠');
                                const isCross = item.includes('❌');
                                const cleanItem = item.replace(/^[-✅⚠❌]\s*/, '');
                                let icon = '✦';
                                let iconColor: string = colors.accent.indigo;

                                if (isCheck) {
                                  icon = '✓';
                                  iconColor = colors.accent.emerald;
                                } else if (isWarning) {
                                  icon = '⚠';
                                  iconColor = colors.accent.amber;
                                } else if (isCross) {
                                  icon = '✗';
                                  iconColor = colors.accent.rose;
                                }

                                return (
                                  <View key={iIdx} style={styles.listItem}>
                                    <View style={[styles.listItemIconContainer, { backgroundColor: iconColor + '1a' }]}>
                                      <Text style={[styles.listItemIcon, { color: iconColor }]}>
                                        {icon}
                                      </Text>
                                    </View>
                                    <Text style={styles.listItemText}>
                                      {parseBoldAndItalic(cleanItem, styles.listItemBaseText)}
                                    </Text>
                                  </View>
                                );
                              })}
                          </View>
                        </View>
                      );

                    case 'timeline':
                      return (
                        <View key={idx} style={styles.timelineContainer}>
                          {comp.heading && (
                            <Text style={styles.timelineHeading}>📅 {comp.heading}</Text>
                          )}
                          <View style={styles.timelineCard}>
                            {content
                              .split('\n')
                              .filter((line) => line.includes('|'))
                              .map((line, tIdx) => {
                                const cells = line
                                  .split('|')
                                  .map((c) => c.trim())
                                  .filter((_, cIdx, arr) => cIdx > 0 && cIdx < arr.length - 1);
                                if (line.includes('---') || tIdx === 0) return null; // skip header or separator

                                const yearText = cells[0] || '';
                                const ratingText = cells[1] || '';
                                const eventText = cells[2] || '';

                                return (
                                  <View key={tIdx} style={styles.timelineItem}>
                                    <View style={styles.timelineDot} />
                                    <View style={styles.timelineContent}>
                                      <View style={styles.timelineHeader}>
                                        <Text style={styles.timelineYear}>{yearText}</Text>
                                        <Text style={styles.timelineRating}>{ratingText}</Text>
                                      </View>
                                      <Text style={styles.timelineDescription}>
                                        {parseBoldAndItalic(eventText, styles.timelineDescriptionText)}
                                      </Text>
                                    </View>
                                  </View>
                                );
                              })}
                          </View>
                        </View>
                      );

                    default:
                      return (
                        <View key={idx} style={styles.defaultParagraph}>
                          <Text style={styles.defaultParagraphText}>
                            {parseBoldAndItalic(content, styles.defaultParagraphText)}
                          </Text>
                        </View>
                      );
                  }
                })}
            </View>
          </View>
        ))}
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    gap: spacing['2xl'],
  },
  decodingContainer: {
    padding: spacing['4xl'],
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  decodingText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    fontStyle: 'italic',
  },

  // Inline markdown styles
  boldText: {
    fontFamily: fonts.bodySemibold,
    color: colors.fg.primary,
  },
  italicText: {
    fontFamily: fonts.body,
    fontStyle: 'italic',
    color: colors.fg.secondary,
  },
  codeText: {
    fontFamily: fonts.mono,
    fontSize: fontSizes.xs,
    color: colors.accent.indigo,
    backgroundColor: 'rgba(99, 102, 241, 0.1)',
    paddingHorizontal: 4,
    borderRadius: radii.sm,
  },

  // Title Block
  titleBlock: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingBottom: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  badgeContainer: {
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.2)',
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radii.full,
  },
  badgeText: {
    fontFamily: fonts.bodySemibold,
    fontSize: 9,
    color: colors.accent.violet,
    letterSpacing: 1.5,
  },
  reportTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes.xl,
    color: colors.fg.primary,
    textAlign: 'center',
  },
  reportSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    fontStyle: 'italic',
    lineHeight: 18,
    paddingHorizontal: spacing.md,
  },

  // Executive Summary
  summaryCard: {
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.md,
  },
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  summaryHeaderIcon: { fontSize: 16 },
  summaryHeaderText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.indigo,
    letterSpacing: 1,
  },
  overallScoreBadge: {
    marginLeft: 'auto',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.full,
  },
  overallScoreText: {
    fontFamily: fonts.bodySemibold,
    fontSize: 10,
    color: colors.accent.emerald,
  },
  metricsGrid: {
    gap: spacing.sm,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.03)',
  },
  metricLabelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  metricEmoji: { fontSize: 14 },
  metricLabel: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
  },
  metricValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  metricValue: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  ratingBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.full,
    borderWidth: 1,
  },
  ratingFavorable: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderColor: 'rgba(16, 185, 129, 0.2)',
  },
  ratingMixed: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    borderColor: 'rgba(245, 158, 11, 0.2)',
  },
  ratingChallenging: {
    backgroundColor: 'rgba(244, 63, 94, 0.1)',
    borderColor: 'rgba(244, 63, 94, 0.2)',
  },
  ratingText: {
    fontFamily: fonts.bodySemibold,
    fontSize: 9,
    color: colors.fg.primary,
  },

  // Sections
  sectionContainer: {
    gap: spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
    paddingBottom: spacing.xs,
  },
  sectionIndicator: {
    width: 3,
    height: 16,
    borderRadius: 2,
    backgroundColor: colors.accent.indigo,
  },
  sectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  componentsContainer: {
    gap: spacing.md,
  },

  // Card component
  componentCard: {
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderRadius: radii.lg,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  componentHeading: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.indigo,
    letterSpacing: 0.5,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.03)',
    paddingBottom: spacing.xs,
  },
  componentBody: {
    lineHeight: 22,
  },
  componentText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    lineHeight: 22,
  },

  // Callout component
  componentCallout: {
    backgroundColor: 'rgba(139, 92, 246, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.15)',
    borderRadius: radii.lg,
    flexDirection: 'row',
    overflow: 'hidden',
  },
  calloutAccent: {
    width: 4,
    backgroundColor: colors.accent.violet,
  },
  calloutContent: {
    padding: spacing.xl,
    flex: 1,
    gap: spacing.xs,
  },
  calloutHeading: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  calloutBody: {
    lineHeight: 20,
  },
  calloutText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    fontStyle: 'italic',
    lineHeight: 20,
  },

  // Table component
  tableContainer: {
    gap: spacing.xs,
  },
  tableHeading: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.sky,
    paddingLeft: 4,
  },
  tableCard: {
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderRadius: radii.lg,
    overflow: 'hidden',
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.03)',
  },
  tableHeaderRow: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  tableBodyRow: {},
  tableCell: {
    flex: 1,
  },
  tableHeaderCell: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.fg.primary,
  },
  tableBodyCell: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.secondary,
  },

  // List component
  listContainer: {
    gap: spacing.xs,
  },
  listHeading: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
    paddingLeft: 4,
  },
  listCard: {
    gap: spacing.sm,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderRadius: radii.lg,
    padding: spacing.lg,
    gap: spacing.md,
  },
  listItemIconContainer: {
    width: 24,
    height: 24,
    borderRadius: radii.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listItemIcon: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
  },
  listItemText: {
    flex: 1,
    lineHeight: 20,
  },
  listItemBaseText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    lineHeight: 20,
  },

  // Timeline component
  timelineContainer: {
    gap: spacing.xs,
  },
  timelineHeading: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.violet,
    paddingLeft: 4,
  },
  timelineCard: {
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    borderRadius: radii.lg,
    padding: spacing.xl,
    gap: spacing.lg,
  },
  timelineItem: {
    flexDirection: 'row',
    gap: spacing.lg,
  },
  timelineDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent.violet,
    marginTop: 6,
  },
  timelineContent: {
    flex: 1,
    gap: spacing.xs,
  },
  timelineHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  timelineYear: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  timelineRating: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.xs,
    color: colors.accent.amber,
  },
  timelineDescription: {
    lineHeight: 20,
  },
  timelineDescriptionText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    lineHeight: 20,
  },

  // Default block
  defaultParagraph: {
    paddingVertical: spacing.xs,
  },
  defaultParagraphText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    lineHeight: 22,
  },
});
