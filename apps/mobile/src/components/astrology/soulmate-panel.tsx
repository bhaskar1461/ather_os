/**
 * Soulmate Panel — AI-generated soulmate portrait with attributes & timeline.
 *
 * Calls POST /astrology/soulmate-portrait with the user's birth chart
 * and gender preference to generate a soulmate profile including:
 * - AI-generated portrait image
 * - Appearance, personality, profession attributes
 * - Astrological indicator justifications
 * - Relationship timeline with yearly ratings
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  Image,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useProfileStore } from '../../store/useProfileStore';
import { apiFetch } from '../../lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../theme/tokens';

interface TimelineEntry {
  date: string;
  rating: string;
  theme: string;
}

interface SoulmateData {
  age_range: string;
  appearance: string;
  portrait_description?: string;
  personality: string;
  profession: string;
  indicators: string[];
  relationship_timeline: TimelineEntry[];
  image_url?: string;
  image_source?: string;
  estimated_birth_date_range?: string;
  birth_date_note?: string;
}

type Gender = 'male' | 'female';

export default function SoulmatePanel() {
  const { getSelectedProfile } = useProfileStore();
  const [soulmateData, setSoulmateData] = useState<SoulmateData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedGender, setSelectedGender] = useState<Gender | null>(null);

  const selectedProfile = getSelectedProfile();

  const generateSoulmate = useCallback(async (gender: Gender) => {
    if (!selectedProfile) {
      Alert.alert('No Profile', 'Please select a birth profile first.');
      return;
    }
    if (!selectedProfile.latitude || !selectedProfile.longitude || !selectedProfile.timezone) {
      Alert.alert('Incomplete Profile', 'Please add birth location to your profile first.');
      return;
    }

    setIsLoading(true);
    setSelectedGender(gender);

    try {
      const [year, month, day] = (selectedProfile.birthDate || '2000-01-01').split('-').map(Number);
      const [hour, minute] = (selectedProfile.birthTime || '12:00').split(':').map(Number);

      const data = await apiFetch<SoulmateData>('/astrology/soulmate-portrait', {
        method: 'POST',
        json: {
          gender,
          year,
          month,
          day,
          hour,
          minute,
          location_lat: selectedProfile.latitude,
          location_lon: selectedProfile.longitude,
          location_timezone: selectedProfile.timezone,
          force_refresh: false,
        },
      });

      setSoulmateData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate soulmate portrait';
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
          Go to the Profile tab to create a birth profile, then come back to discover your cosmic soulmate.
        </Text>
      </View>
    );
  }

  // Gender Selection
  if (!soulmateData && !isLoading) {
    return (
      <View style={styles.genderSection}>
        <Text style={styles.genderTitle}>Who are you looking for?</Text>
        <Text style={styles.genderSubtitle}>
          Select the gender of your ideal partner to generate a personalized cosmic soulmate portrait
        </Text>

        <View style={styles.genderRow}>
          <Pressable
            style={({ pressed }) => [styles.genderCard, pressed && { opacity: 0.8, transform: [{ scale: 0.97 }] }]}
            onPress={() => generateSoulmate('male')}
          >
            <LinearGradient
              colors={['rgba(99, 102, 241, 0.15)', 'rgba(56, 189, 248, 0.08)']}
              style={styles.genderGradient}
            >
              <Text style={styles.genderEmoji}>♂</Text>
              <Text style={styles.genderLabel}>Male</Text>
            </LinearGradient>
          </Pressable>

          <Pressable
            style={({ pressed }) => [styles.genderCard, pressed && { opacity: 0.8, transform: [{ scale: 0.97 }] }]}
            onPress={() => generateSoulmate('female')}
          >
            <LinearGradient
              colors={['rgba(139, 92, 246, 0.15)', 'rgba(244, 63, 94, 0.08)']}
              style={styles.genderGradient}
            >
              <Text style={styles.genderEmoji}>♀</Text>
              <Text style={styles.genderLabel}>Female</Text>
            </LinearGradient>
          </Pressable>
        </View>
      </View>
    );
  }

  // Loading
  if (isLoading) {
    return (
      <View style={styles.loadingCard}>
        <ActivityIndicator size="large" color={colors.accent.violet} />
        <Text style={styles.loadingText}>Consulting the stars…</Text>
        <Text style={styles.loadingSubtext}>
          Analyzing 7th house, Venus, Moon, and Navamsa alignments to reveal your soulmate portrait
        </Text>
      </View>
    );
  }

  // Results
  return (
    <View>
      {/* Portrait Card */}
      {soulmateData?.image_url && soulmateData.image_source !== 'symbolic_fallback' && (
        <View style={styles.portraitCard}>
          <Image
            source={{ uri: soulmateData.image_url.startsWith('data:') ? soulmateData.image_url : `data:image/png;base64,${soulmateData.image_url}` }}
            style={styles.portraitImage}
            resizeMode="cover"
          />
          <LinearGradient
            colors={['transparent', 'rgba(5, 5, 7, 0.9)']}
            style={styles.portraitOverlay}
          >
            <Text style={styles.portraitTitle}>Your Cosmic Soulmate</Text>
            <Text style={styles.portraitAge}>Age Range: {soulmateData.age_range}</Text>
          </LinearGradient>
        </View>
      )}

      {/* Attributes Grid */}
      <View style={styles.attributesSection}>
        <AttributeCard icon="✦" title="Appearance" value={soulmateData!.appearance} accent={colors.accent.sky} />
        <AttributeCard icon="◉" title="Personality" value={soulmateData!.personality} accent={colors.accent.violet} />
        <AttributeCard icon="◆" title="Profession" value={soulmateData!.profession} accent={colors.accent.amber} />
      </View>

      {/* Astrological Indicators */}
      <View style={styles.indicatorsCard}>
        <Text style={styles.sectionTitle}>✦ Astrological Indicators</Text>
        {soulmateData!.indicators.map((indicator, idx) => (
          <View key={idx} style={styles.indicatorRow}>
            <View style={[styles.indicatorDot, { backgroundColor: [colors.accent.indigo, colors.accent.violet, colors.accent.sky, colors.accent.amber][idx % 4] }]} />
            <Text style={styles.indicatorText}>{indicator}</Text>
          </View>
        ))}
      </View>

      {/* Relationship Timeline */}
      <View style={styles.timelineCard}>
        <Text style={styles.sectionTitle}>◉ Relationship Timeline</Text>
        {soulmateData!.relationship_timeline.map((entry, idx) => (
          <View key={idx} style={styles.timelineRow}>
            <View style={styles.timelineDot} />
            {idx < soulmateData!.relationship_timeline.length - 1 && (
              <View style={styles.timelineLine} />
            )}
            <View style={styles.timelineContent}>
              <View style={styles.timelineHeader}>
                <Text style={styles.timelineDate}>{entry.date}</Text>
                <Text style={styles.timelineRating}>{entry.rating}</Text>
              </View>
              <Text style={styles.timelineTheme}>{entry.theme}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Regenerate */}
      <Pressable
        style={({ pressed }) => [styles.regenerateButton, pressed && { opacity: 0.7 }]}
        onPress={() => {
          setSoulmateData(null);
          setSelectedGender(null);
        }}
      >
        <Text style={styles.regenerateText}>↻ Generate New Portrait</Text>
      </Pressable>
    </View>
  );
}

// ── Sub-component ───────────────────────────────────────────────────────────

function AttributeCard({ icon, title, value, accent }: { icon: string; title: string; value: string; accent: string }) {
  return (
    <View style={styles.attributeCard}>
      <View style={styles.attributeHeader}>
        <Text style={[styles.attributeIcon, { color: accent }]}>{icon}</Text>
        <Text style={styles.attributeTitle}>{title}</Text>
      </View>
      <Text style={styles.attributeValue}>{value}</Text>
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────

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
  placeholderIcon: { fontSize: 40, color: colors.fg.faint, marginBottom: spacing.lg },
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

  // Gender selection
  genderSection: {
    marginTop: spacing['2xl'],
    alignItems: 'center',
  },
  genderTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.xl,
    color: colors.fg.primary,
    marginBottom: spacing.sm,
  },
  genderSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: spacing['3xl'],
    paddingHorizontal: spacing.lg,
  },
  genderRow: {
    flexDirection: 'row',
    gap: spacing.lg,
    width: '100%',
  },
  genderCard: {
    flex: 1,
    borderRadius: radii.xl,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
  },
  genderGradient: {
    alignItems: 'center',
    paddingVertical: spacing['4xl'],
    borderRadius: radii.xl,
  },
  genderEmoji: {
    fontSize: 40,
    color: colors.fg.primary,
    marginBottom: spacing.md,
  },
  genderLabel: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },

  // Loading
  loadingCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['4xl'],
    alignItems: 'center',
    marginTop: spacing['2xl'],
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
    lineHeight: 20,
  },

  // Portrait
  portraitCard: {
    borderRadius: radii.xl,
    overflow: 'hidden',
    marginTop: spacing.lg,
    height: 400,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
  },
  portraitImage: {
    width: '100%',
    height: '100%',
  },
  portraitOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: spacing['2xl'],
    paddingTop: spacing['5xl'],
  },
  portraitTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes.xl,
    color: colors.fg.primary,
  },
  portraitAge: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: spacing.xs,
  },

  // Attributes
  attributesSection: {
    gap: spacing.md,
    marginTop: spacing['2xl'],
  },
  attributeCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.xl,
  },
  attributeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  attributeIcon: { fontSize: 16 },
  attributeTitle: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  attributeValue: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.secondary,
    lineHeight: 22,
  },

  // Indicators
  indicatorsCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
    marginTop: spacing['2xl'],
  },
  sectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.lg,
  },
  indicatorRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  indicatorDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
  },
  indicatorText: {
    flex: 1,
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    lineHeight: 20,
  },

  // Timeline
  timelineCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
    marginTop: spacing['2xl'],
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.xl,
    position: 'relative',
  },
  timelineDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.accent.violet,
    marginTop: 4,
    marginRight: spacing.lg,
    zIndex: 1,
  },
  timelineLine: {
    position: 'absolute',
    left: 5,
    top: 16,
    bottom: -20,
    width: 2,
    backgroundColor: colors.accent.violetMuted,
  },
  timelineContent: {
    flex: 1,
  },
  timelineHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  timelineDate: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  timelineRating: {
    fontSize: fontSizes.sm,
  },
  timelineTheme: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
  },

  // Regenerate
  regenerateButton: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    marginTop: spacing['2xl'],
    marginBottom: spacing['2xl'],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
  },
  regenerateText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
  },
});
