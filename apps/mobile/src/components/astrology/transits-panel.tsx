/**
 * Transits Panel — Daily planetary transit horoscope.
 *
 * Calls POST /astrology/transit with the user's natal chart details
 * and current location/timezone to get today's transit placements
 * and an AI-generated daily guidance horoscope.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useProfileStore, Profile } from '../../store/useProfileStore';
import { apiFetch } from '../../lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../theme/tokens';

interface TransitPlacement {
  planet: string;
  transit_sign: string;
  natal_house: number;
  degrees: number;
}

interface TransitResponse {
  date: string;
  transit_placements: TransitPlacement[];
  horoscope: string;
}

// Planet display config
const PLANET_ICONS: Record<string, string> = {
  sun: '☉',
  moon: '☽',
  mars: '♂',
  mercury: '☿',
  jupiter: '♃',
  venus: '♀',
  saturn: '♄',
  rahu: '☊',
  ketu: '☋',
};

const PLANET_COLORS: Record<string, string> = {
  sun: colors.accent.amber,
  moon: colors.accent.sky,
  mars: colors.accent.rose,
  mercury: colors.accent.emerald,
  jupiter: colors.accent.amber,
  venus: colors.accent.violet,
  saturn: colors.fg.muted,
  rahu: colors.fg.faint,
  ketu: colors.fg.faint,
};

export default function TransitsPanel() {
  const { getSelectedProfile } = useProfileStore();
  const [transitData, setTransitData] = useState<TransitResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const selectedProfile = getSelectedProfile();

  const generateTransits = useCallback(async (forceRefresh = false) => {
    if (!selectedProfile) {
      Alert.alert('No Profile', 'Please select a birth profile first.');
      return;
    }
    if (!selectedProfile.latitude || !selectedProfile.longitude || !selectedProfile.timezone) {
      Alert.alert('Incomplete Profile', 'Please add birth location to your profile first.');
      return;
    }

    setIsLoading(true);
    try {
      const [year, month, day] = (selectedProfile.birthDate || '2000-01-01').split('-').map(Number);
      const [hour, minute] = (selectedProfile.birthTime || '12:00').split(':').map(Number);

      const data = await apiFetch<TransitResponse>('/astrology/transit', {
        method: 'POST',
        json: {
          birth_year: year,
          birth_month: month,
          birth_day: day,
          birth_hour: hour,
          birth_minute: minute,
          birth_lat: selectedProfile.latitude,
          birth_lon: selectedProfile.longitude,
          birth_timezone: selectedProfile.timezone,
          current_lat: selectedProfile.latitude,
          current_lon: selectedProfile.longitude,
          current_timezone: selectedProfile.timezone,
          force_refresh: forceRefresh,
        },
      });

      setTransitData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate transits';
      Alert.alert('Error', msg);
    } finally {
      setIsLoading(false);
    }
  }, [selectedProfile]);

  if (!selectedProfile) {
    return (
      <View style={styles.placeholderCard}>
        <Text style={styles.placeholderIcon}>◎</Text>
        <Text style={styles.placeholderTitle}>No Profile Selected</Text>
        <Text style={styles.placeholderText}>
          Go to the Profile tab to create a birth profile, then come back to view your daily transits.
        </Text>
      </View>
    );
  }

  return (
    <View>
      {/* Generate / Refresh Button */}
      {!transitData && !isLoading && (
        <Pressable
          style={({ pressed }) => [styles.generateButton, pressed && { opacity: 0.8 }]}
          onPress={() => generateTransits(false)}
        >
          <LinearGradient
            colors={['#38bdf8', '#6366f1']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.generateGradient}
          >
            <Text style={styles.generateIcon}>🌙</Text>
            <Text style={styles.generateText}>View Today's Transits</Text>
          </LinearGradient>
        </Pressable>
      )}

      {/* Loading */}
      {isLoading && (
        <View style={styles.loadingCard}>
          <ActivityIndicator size="large" color={colors.accent.sky} />
          <Text style={styles.loadingText}>Computing transit positions…</Text>
          <Text style={styles.loadingSubtext}>
            Mapping current planetary positions to your natal houses
          </Text>
        </View>
      )}

      {/* Transit Data */}
      {transitData && !isLoading && (
        <View>
          {/* Date Header */}
          <View style={styles.dateHeader}>
            <Text style={styles.dateIcon}>📅</Text>
            <View>
              <Text style={styles.dateTitle}>Daily Transit Guidance</Text>
              <Text style={styles.dateSubtitle}>{transitData.date}</Text>
            </View>
            <Pressable
              style={styles.refreshButton}
              onPress={() => generateTransits(true)}
            >
              <Text style={styles.refreshIcon}>↻</Text>
            </Pressable>
          </View>

          {/* Transit Planet Cards */}
          <View style={styles.planetsGrid}>
            {transitData.transit_placements.map((tp) => (
              <View key={tp.planet} style={styles.planetCard}>
                <Text style={[styles.planetIcon, { color: PLANET_COLORS[tp.planet] || colors.fg.primary }]}>
                  {PLANET_ICONS[tp.planet] || '●'}
                </Text>
                <Text style={styles.planetName}>
                  {tp.planet.charAt(0).toUpperCase() + tp.planet.slice(1)}
                </Text>
                <Text style={styles.planetSign}>{tp.transit_sign}</Text>
                <View style={styles.houseChip}>
                  <Text style={styles.houseChipText}>House {tp.natal_house}</Text>
                </View>
              </View>
            ))}
          </View>

          {/* AI Horoscope */}
          <View style={styles.horoscopeCard}>
            <Text style={styles.horoscopeTitle}>✦ Daily Guidance</Text>
            {renderTransitMarkdown(transitData.horoscope)}
          </View>
        </View>
      )}
    </View>
  );
}

// ── Simple markdown renderer ────────────────────────────────────────────────

function renderTransitMarkdown(text: string) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      elements.push(<View key={`s-${key++}`} style={{ height: spacing.sm }} />);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <Text key={`h2-${key++}`} style={mdStyles.h2}>{trimmed.slice(3)}</Text>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <Text key={`h3-${key++}`} style={mdStyles.h3}>{trimmed.slice(4)}</Text>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <View key={`li-${key++}`} style={mdStyles.bulletRow}>
          <Text style={mdStyles.bullet}>•</Text>
          <Text style={mdStyles.bulletText}>{parseBold(trimmed.slice(2))}</Text>
        </View>
      );
    } else {
      elements.push(
        <Text key={`p-${key++}`} style={mdStyles.paragraph}>{parseBold(trimmed)}</Text>
      );
    }
  }

  return <View style={{ gap: spacing.xs }}>{elements}</View>;
}

function parseBold(text: string): React.ReactNode[] {
  const parts = text.split('**');
  return parts.map((part, i) =>
    i % 2 === 1
      ? <Text key={`b-${i}`} style={mdStyles.bold}>{part}</Text>
      : <Text key={`t-${i}`}>{part}</Text>
  );
}

const mdStyles = StyleSheet.create({
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
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingLeft: spacing.sm,
  },
  bullet: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.accent.sky,
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
  bold: {
    fontFamily: fonts.bodySemibold,
    color: colors.fg.primary,
  },
});

// ── Component styles ────────────────────────────────────────────────────────

const styles = StyleSheet.create({
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
  generateIcon: { fontSize: 20 },
  generateText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: '#fff',
  },
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
  dateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  dateIcon: { fontSize: 24 },
  dateTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
  },
  dateSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: 2,
  },
  refreshButton: {
    marginLeft: 'auto',
    backgroundColor: colors.bg.glass,
    borderRadius: radii.full,
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
  },
  refreshIcon: {
    fontSize: 18,
    color: colors.accent.sky,
  },
  planetsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing['2xl'],
  },
  planetCard: {
    width: '30%',
    flexGrow: 1,
    minWidth: 95,
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.md,
    alignItems: 'center',
    gap: spacing.xs,
  },
  planetIcon: {
    fontSize: 24,
  },
  planetName: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  planetSign: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
  },
  houseChip: {
    backgroundColor: colors.accent.indigoMuted,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.full,
  },
  houseChipText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 10,
    color: colors.accent.indigo,
  },
  horoscopeCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
  },
  horoscopeTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.accent.sky,
    marginBottom: spacing.md,
  },
});
