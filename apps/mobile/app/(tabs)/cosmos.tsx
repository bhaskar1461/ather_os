/**
 * Cosmos Screen — main astrology hub with segmented sub-tab control.
 *
 * Sub-sections: Reports, Compatibility, Transits, Soulmate
 * Each section renders its own component based on the active segment.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ScrollView,
  Animated,
  RefreshControl,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useProfileStore, Profile } from '../../src/store/useProfileStore';
import { apiFetch, apiStream } from '../../src/lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../src/theme/tokens';
import ChartWheel from '../../src/components/astrology/chart-wheel';
import CompatibilityPanel from '../../src/components/astrology/compatibility-panel';
import TransitsPanel from '../../src/components/astrology/transits-panel';
import SoulmatePanel from '../../src/components/astrology/soulmate-panel';

type CosmosTab = 'reports' | 'compatibility' | 'transits' | 'soulmate';

const TABS: { key: CosmosTab; label: string; icon: string }[] = [
  { key: 'reports', label: 'Reports', icon: '📜' },
  { key: 'compatibility', label: 'Match', icon: '💫' },
  { key: 'transits', label: 'Transits', icon: '🌙' },
  { key: 'soulmate', label: 'Soulmate', icon: '✨' },
];

export default function CosmosScreen() {
  const [activeTab, setActiveTab] = useState<CosmosTab>('reports');
  const [refreshing, setRefreshing] = useState(false);
  const { profiles, selectedProfileId, fetchProfiles, getSelectedProfile } = useProfileStore();
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    fetchProfiles();
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim, fetchProfiles]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchProfiles();
    setRefreshing(false);
  }, [fetchProfiles]);

  const selectedProfile = getSelectedProfile();

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#050507', '#080818', '#050507']}
        style={StyleSheet.absoluteFill}
      />

      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <Animated.View style={[styles.inner, { opacity: fadeAnim }]}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.headerTitle}>Cosmic Hub</Text>
              <Text style={styles.headerSubtitle}>
                {selectedProfile
                  ? `Reading for ${selectedProfile.name}`
                  : 'Select a profile to begin'}
              </Text>
            </View>
            <Text style={styles.headerIcon}>✦</Text>
          </View>

          {/* Segmented Control */}
          <View style={styles.segmentedControl}>
            {TABS.map((tab) => (
              <Pressable
                key={tab.key}
                style={[
                  styles.segment,
                  activeTab === tab.key && styles.segmentActive,
                ]}
                onPress={() => setActiveTab(tab.key)}
              >
                <Text style={styles.segmentIcon}>{tab.icon}</Text>
                <Text
                  style={[
                    styles.segmentLabel,
                    activeTab === tab.key && styles.segmentLabelActive,
                  ]}
                >
                  {tab.label}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Content Area */}
          <ScrollView
            style={styles.contentScroll}
            contentContainerStyle={styles.contentContainer}
            showsVerticalScrollIndicator={false}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={colors.accent.indigo}
              />
            }
          >
            {activeTab === 'compatibility' ? (
              <CompatibilityPanel />
            ) : !selectedProfile ? (
              <NoProfilePlaceholder />
            ) : activeTab === 'reports' ? (
              <ReportsSection profile={selectedProfile} />
            ) : activeTab === 'transits' ? (
              <TransitsPanel />
            ) : (
              <SoulmatePanel />
            )}
          </ScrollView>
        </Animated.View>
      </SafeAreaView>
    </View>
  );
}

// ── Reports Section ─────────────────────────────────────────────────────────

import VisualReportRenderer from '../../src/components/astrology/visual-report-renderer';
import { documentDirectory, writeAsStringAsync } from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { getAccessToken } from '../../src/lib/secure-storage';
import { API_BASE_URL } from '../../src/lib/api-client';

function ReportsSection({ profile }: { profile: Profile }) {
  const [chartData, setChartData] = useState<any>(null);
  const [reading, setReading] = useState<string>('');
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  const isJsonReading = (text: string) => {
    const trimmed = text.trim();
    return trimmed.startsWith('{') || trimmed.startsWith('[') || trimmed.startsWith('```json') || trimmed.startsWith('```');
  };

  const exportToPdf = async () => {
    setIsExportingPdf(true);
    try {
      const token = await getAccessToken();
      const pdfUri = `${documentDirectory}Cosmic_Hub_Report.pdf`;

      const response = await fetch(`${API_BASE_URL}/astrology/reading/export-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'bypass-tunnel-warning': 'true',
        },
        body: JSON.stringify({
          content_markdown: reading,
          metadata: {
            name: profile.name,
            analysis_date: new Date().toLocaleDateString(),
            birth_date: profile.birthDate,
            birth_time: profile.birthTime,
            birth_location: profile.birthPlace,
          }
        })
      });

      if (!response.ok) {
        throw new Error('Server returned status ' + response.status);
      }

      const blob = await response.blob();
      const reader = new FileReader();
      reader.onloadend = async () => {
        try {
          const resultStr = reader.result as string;
          const base64data = resultStr.split(',')[1];
          if (!base64data) {
            throw new Error('Could not parse PDF content.');
          }
          await writeAsStringAsync(pdfUri, base64data, {
            encoding: 'base64',
          });
          await Sharing.shareAsync(pdfUri, {
            mimeType: 'application/pdf',
            dialogTitle: 'Cosmic Hub Report',
            UTI: 'com.adobe.pdf',
          });
        } catch (innerErr: unknown) {
          const msg = innerErr instanceof Error ? innerErr.message : 'Failed to save or share PDF';
          Alert.alert('Error', msg);
        } finally {
          setIsExportingPdf(false);
        }
      };
      reader.onerror = () => {
        Alert.alert('Error', 'Failed to read PDF binary stream.');
        setIsExportingPdf(false);
      };
      reader.readAsDataURL(blob);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'PDF export failed';
      Alert.alert('Error', msg);
      setIsExportingPdf(false);
    }
  };

  const generateChart = async () => {
    if (!profile.latitude || !profile.longitude || !profile.timezone) {
      Alert.alert('Incomplete Profile', 'Please add birth location to your profile first.');
      return;
    }

    setIsLoadingChart(true);
    setReading('');

    try {
      // Parse birth date/time
      const [year, month, day] = (profile.birthDate || '2000-01-01').split('-').map(Number);
      const [hour, minute] = (profile.birthTime || '12:00').split(':').map(Number);

      // Fetch chart data
      const chart = await apiFetch('/astrology/chart/v2', {
        method: 'POST',
        json: {
          year, month, day, hour, minute,
          location_name: profile.birthPlace,
          location_lat: profile.latitude,
          location_lon: profile.longitude,
          location_timezone: profile.timezone,
        },
      });

      setChartData(chart);
      setIsLoadingChart(false);

      // Stream reading
      setIsStreaming(true);
      const stream = apiStream('/astrology/reading/v2', {
        method: 'POST',
        json: {
          year, month, day, hour, minute,
          location_name: profile.birthPlace,
          location_lat: profile.latitude,
          location_lon: profile.longitude,
          location_timezone: profile.timezone,
          stream: true,
          report_type: 'full_report',
        },
      });

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setReading(accumulated);
      }
      setIsStreaming(false);
    } catch (err: unknown) {
      setIsLoadingChart(false);
      setIsStreaming(false);
      const msg = err instanceof Error ? err.message : 'Chart generation failed';
      Alert.alert('Error', msg);
    }
  };

  return (
    <View>
      {/* Generate Button */}
      {!chartData && !isLoadingChart && (
        <Pressable
          style={({ pressed }) => [
            styles.generateButton,
            pressed && { opacity: 0.8 },
          ]}
          onPress={generateChart}
        >
          <LinearGradient
            colors={['#6366f1', '#8b5cf6']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.generateGradient}
          >
            <Text style={styles.generateIcon}>✦</Text>
            <Text style={styles.generateText}>Generate Birth Chart</Text>
          </LinearGradient>
        </Pressable>
      )}

      {/* Loading */}
      {isLoadingChart && (
        <View style={styles.loadingCard}>
          <ActivityIndicator size="large" color={colors.accent.indigo} />
          <Text style={styles.loadingText}>Calculating planetary positions…</Text>
          <Text style={styles.loadingSubtext}>
            Computing sidereal coordinates with Lahiri ayanamsa
          </Text>
        </View>
      )}

      {/* Chart Wheel */}
      {chartData && (
        <View style={styles.chartSection}>
          <Text style={styles.sectionTitle}>Birth Chart (Rasi)</Text>
          <ChartWheel
            planets={chartData.chart?.planets || {}}
            ascendant={chartData.chart?.ascendant || { sign: 'Aries', sign_index: 0 }}
          />
        </View>
      )}

      {/* Scores */}
      {chartData?.rules?.scores && (
        <View style={styles.scoresGrid}>
          {Object.entries(chartData.rules.scores as Record<string, number>).map(([key, value]) => (
            <View key={key} style={styles.scoreCard}>
              <Text style={styles.scoreValue}>{value}</Text>
              <Text style={styles.scoreLabel}>
                {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Reading Content */}
      {(reading || isStreaming) && (
        <View style={styles.readingCard}>
          <View style={styles.readingHeaderRow}>
            <Text style={styles.sectionTitle}>Your Reading</Text>
            {reading && !isStreaming && (
              <Pressable
                style={({ pressed }) => [styles.pdfButton, pressed && { opacity: 0.8 }]}
                onPress={exportToPdf}
                disabled={isExportingPdf}
              >
                {isExportingPdf ? (
                  <ActivityIndicator size="small" color={colors.accent.indigo} />
                ) : (
                  <Text style={styles.pdfButtonText}>📥 Export PDF</Text>
                )}
              </Pressable>
            )}
          </View>
          {isJsonReading(reading) ? (
            <VisualReportRenderer json={reading} />
          ) : (
            renderAstrologyMarkdown(reading)
          )}
          {isStreaming && (
            <View style={styles.streamingIndicator}>
              <ActivityIndicator size="small" color={colors.accent.violet} />
              <Text style={styles.streamingText}>Generating insight…</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

// ── Placeholder Components ──────────────────────────────────────────────────

function NoProfilePlaceholder() {
  return (
    <View style={styles.placeholderCard}>
      <Text style={styles.placeholderIcon}>◎</Text>
      <Text style={styles.placeholderTitle}>No Profile Selected</Text>
      <Text style={styles.placeholderText}>
        Go to the Profile tab to create a birth profile, then come back to generate your cosmic reading.
      </Text>
    </View>
  );
}

function ComingSoonSection({ title, icon }: { title: string; icon: string }) {
  return (
    <View style={styles.placeholderCard}>
      <Text style={styles.placeholderIcon}>{icon}</Text>
      <Text style={styles.placeholderTitle}>{title}</Text>
      <Text style={styles.placeholderText}>
        This section is being built. It will be available in the next update.
      </Text>
    </View>
  );
}

// ── Markdown Parser ──────────────────────────────────────────────────────────

function renderAstrologyMarkdown(text: string) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let keyCounter = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) {
      elements.push(<View key={`space-${keyCounter++}`} style={{ height: spacing.sm }} />);
      continue;
    }

    if (line.startsWith('# ')) {
      elements.push(
        <Text key={`h1-${keyCounter++}`} style={mdStyles.h1}>
          {line.slice(2)}
        </Text>
      );
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <Text key={`h2-${keyCounter++}`} style={mdStyles.h2}>
          {line.slice(3)}
        </Text>
      );
      continue;
    }
    if (line.startsWith('### ')) {
      elements.push(
        <Text key={`h3-${keyCounter++}`} style={mdStyles.h3}>
          {line.slice(4)}
        </Text>
      );
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      const cleanLine = line.slice(2);
      elements.push(
        <View key={`li-${keyCounter++}`} style={mdStyles.bulletRow}>
          <Text style={mdStyles.bullet}>•</Text>
          <Text style={mdStyles.bulletText}>{parseInlineBold(cleanLine)}</Text>
        </View>
      );
      continue;
    }

    elements.push(
      <Text key={`p-${keyCounter++}`} style={mdStyles.paragraph}>
        {parseInlineBold(line)}
      </Text>
    );
  }

  return <View style={{ gap: spacing.xs }}>{elements}</View>;
}

function parseInlineBold(text: string): React.ReactNode[] {
  const parts = text.split('**');
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return (
        <Text key={`bold-${index}`} style={mdStyles.boldText}>
          {part}
        </Text>
      );
    }
    return (
      <Text key={`plain-${index}`}>
        {part}
      </Text>
    );
  });
}

const mdStyles = StyleSheet.create({
  h1: {
    fontFamily: fonts.display,
    fontSize: fontSizes.xl,
    color: colors.fg.primary,
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
  },
  h2: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  h3: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  paragraph: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.secondary,
    lineHeight: 22,
    marginBottom: spacing.xs,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingLeft: spacing.sm,
    marginBottom: spacing.xs,
  },
  bullet: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.accent.indigo,
    marginRight: spacing.sm,
    lineHeight: 22,
  },
  bulletText: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.secondary,
    lineHeight: 22,
  },
  boldText: {
    fontFamily: fonts.bodySemibold,
    color: colors.fg.primary,
  },
});

// ── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.deep },
  safeArea: { flex: 1 },
  inner: { flex: 1 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing['2xl'],
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes['2xl'],
    color: colors.fg.primary,
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: 2,
  },
  headerIcon: {
    fontSize: 28,
    color: colors.accent.indigo,
  },
  segmentedControl: {
    flexDirection: 'row',
    marginHorizontal: spacing['2xl'],
    marginVertical: spacing.md,
    backgroundColor: colors.bg.card,
    borderRadius: radii.lg,
    padding: spacing.xs,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
  },
  segment: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radii.md,
  },
  segmentActive: {
    backgroundColor: colors.accent.indigoMuted,
  },
  segmentIcon: {
    fontSize: 16,
    marginBottom: 2,
  },
  segmentLabel: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
  },
  segmentLabelActive: {
    color: colors.accent.indigo,
  },
  contentScroll: { flex: 1 },
  contentContainer: {
    paddingHorizontal: spacing['2xl'],
    paddingBottom: spacing['5xl'],
  },

  // Generate button
  generateButton: {
    borderRadius: radii.lg,
    overflow: 'hidden',
    marginTop: spacing.lg,
  },
  generateGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
    borderRadius: radii.lg,
    gap: spacing.sm,
  },
  generateIcon: { fontSize: 20, color: '#fff' },
  generateText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: '#fff',
  },

  // Loading
  loadingCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['3xl'],
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  loadingText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
    marginTop: spacing.lg,
  },
  loadingSubtext: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: spacing.xs,
    textAlign: 'center',
  },

  // Chart section
  chartSection: {
    marginTop: spacing['2xl'],
  },
  sectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.md,
  },

  // Scores grid
  scoresGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing['2xl'],
  },
  scoreCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.lg,
    alignItems: 'center',
  },
  scoreValue: {
    fontFamily: fonts.display,
    fontSize: fontSizes['2xl'],
    color: colors.accent.amber,
  },
  scoreLabel: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
    marginTop: spacing.xs,
    textAlign: 'center',
    textTransform: 'capitalize',
  },

  // Reading
  readingCard: {
    marginTop: spacing['2xl'],
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
  },
  readingHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  pdfButton: {
    backgroundColor: 'rgba(99, 102, 241, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(99, 102, 241, 0.2)',
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  pdfButtonText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.indigo,
  },
  readingText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.secondary,
    lineHeight: 24,
  },
  streamingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  streamingText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.accent.violet,
  },

  // Placeholders
  placeholderCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['4xl'],
    alignItems: 'center',
    marginTop: spacing['2xl'],
  },
  placeholderIcon: {
    fontSize: 40,
    color: colors.fg.faint,
    marginBottom: spacing.lg,
  },
  placeholderTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.sm,
  },
  placeholderText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
  },
});
