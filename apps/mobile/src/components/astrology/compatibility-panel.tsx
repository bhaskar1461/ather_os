/**
 * Compatibility Panel — Ashta Kuta Guna Milan score visualization.
 *
 * Features:
 *  - Dual profile picker (Partner A / Partner B from saved profiles)
 *  - Animated score ring showing total / 36 points
 *  - 8 Kuta breakdown with individual gauge bars
 *  - Advanced compatibility indicators (Manglik, Rajju, Vedha)
 *  - Suitability matrix (romantic, platonic, business, mentorship)
 *  - Streamed LLM reading for partnership synthesis
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Animated,
  Easing,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G, Text as SvgTextEl } from 'react-native-svg';
import { useProfileStore, Profile } from '../../store/useProfileStore';
import { apiFetch, apiStream } from '../../lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../theme/tokens';

// ── Types ───────────────────────────────────────────────────────────────────

interface KutaBreakdown {
  score: number;
  max: number;
  groom?: string;
  bride?: string;
  has_dosha?: boolean;
  has_kuta?: boolean;
  cancelled?: boolean;
  description?: string;
  distance?: number;
  [key: string]: any;
}

interface AdvancedCompat {
  kuja_dosha: {
    partner_a_manglik: boolean;
    partner_a_reason: string;
    partner_b_manglik: boolean;
    partner_b_reason: string;
    status: string;
    compatible: boolean;
    reason: string;
  };
  suitability?: {
    romantic_marriage: number;
    platonic_friendship: number;
    business_professional: number;
    mentorship_growth: number;
    best_suited: string;
  };
  [key: string]: any;
}

interface CompatResult {
  score: number;
  breakdown: Record<string, KutaBreakdown>;
  reading: string;
  advanced_compatibility?: AdvancedCompat;
  partner_a_chart?: { planets: any; ascendant: any };
  partner_b_chart?: { planets: any; ascendant: any };
}

// ── Kuta Guide ──────────────────────────────────────────────────────────────

const KUTA_INFO: Record<string, { title: string; icon: string; meaning: string }> = {
  varna:        { title: 'Shared Values',       icon: '🏛',  meaning: 'Spiritual and life-purpose alignment' },
  vashya:       { title: 'Mutual Pull',         icon: '🧲',  meaning: 'Balance of influence and attraction' },
  tara:         { title: 'Supportive Rhythm',   icon: '⭐',  meaning: 'How your individual rhythms harmonize' },
  yoni:         { title: 'Comfort & Chemistry', icon: '💞',  meaning: 'Instinctive closeness and affection' },
  graha_maitri: { title: 'Mental Rapport',      icon: '🧠',  meaning: 'Intellectual wavelength and communication' },
  gana:         { title: 'Temperament',         icon: '🔥',  meaning: 'How your natures interact daily' },
  bhakoot:      { title: 'Emotional Bond',      icon: '💜',  meaning: 'Deep emotional and karmic connection' },
  nadi:         { title: 'Health & Vitality',    icon: '🌿',  meaning: 'Physiological and energetic harmony' },
};

const KUTA_ORDER = ['varna', 'vashya', 'tara', 'yoni', 'graha_maitri', 'gana', 'bhakoot', 'nadi'];

// ── Main Component ──────────────────────────────────────────────────────────

export default function CompatibilityPanel() {
  const { profiles } = useProfileStore();
  const [partnerA, setPartnerA] = useState<Profile | null>(null);
  const [partnerB, setPartnerB] = useState<Profile | null>(null);
  const [result, setResult] = useState<CompatResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [reading, setReading] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
  }, [fadeAnim]);

  // Auto-select first two profiles
  useEffect(() => {
    if (profiles.length >= 1 && !partnerA) setPartnerA(profiles[0]);
    if (profiles.length >= 2 && !partnerB) setPartnerB(profiles[1]);
  }, [profiles, partnerA, partnerB]);

  const calculateCompatibility = async () => {
    if (!partnerA || !partnerB) {
      Alert.alert('Select Profiles', 'Please select two birth profiles to compare.');
      return;
    }
    if (!partnerA.latitude || !partnerA.longitude || !partnerA.timezone ||
        !partnerB.latitude || !partnerB.longitude || !partnerB.timezone) {
      Alert.alert('Incomplete Profiles', 'Both profiles need birth date, time, and location.');
      return;
    }
    if (partnerA.id === partnerB.id) {
      Alert.alert('Same Profile', 'Please select two different profiles.');
      return;
    }

    setIsLoading(true);
    setResult(null);
    setReading('');

    try {
      const parseBirth = (p: Profile) => {
        const [y, m, d] = (p.birthDate || '2000-01-01').split('-').map(Number);
        const [h, min] = (p.birthTime || '12:00').split(':').map(Number);
        return {
          year: y, month: m, day: d, hour: h, minute: min,
          location_name: p.birthPlace || 'Unknown',
          location_lat: p.latitude!,
          location_lon: p.longitude!,
          location_timezone: p.timezone!,
        };
      };

      const data = await apiFetch<CompatResult>('/astrology/compatibility', {
        method: 'POST',
        json: {
          partner_a: parseBirth(partnerA),
          partner_b: parseBirth(partnerB),
          partner_a_name: partnerA.name,
          partner_b_name: partnerB.name,
        },
      });

      setResult(data);
      if (data.reading) setReading(data.reading);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Calculation failed';
      Alert.alert('Error', msg);
    } finally {
      setIsLoading(false);
    }
  };

  const eligibleProfiles = profiles.filter(
    (p) => p.latitude && p.longitude && p.timezone && p.birthDate && p.birthTime
  );

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      {/* ─── Profile Picker ──────────────────────────────────────────── */}
      <View style={styles.pickerSection}>
        <Text style={styles.sectionTitle}>Compare Two Charts</Text>

        <View style={styles.pickerRow}>
          <ProfilePicker
            label="Partner A"
            selected={partnerA}
            profiles={eligibleProfiles}
            onSelect={setPartnerA}
            color={colors.accent.indigo}
          />
          <View style={styles.pickerDivider}>
            <Text style={styles.vsText}>VS</Text>
          </View>
          <ProfilePicker
            label="Partner B"
            selected={partnerB}
            profiles={eligibleProfiles}
            onSelect={setPartnerB}
            color={colors.accent.violet}
          />
        </View>

        {/* Calculate Button */}
        <Pressable
          style={({ pressed }) => [
            styles.calcButton,
            pressed && { opacity: 0.8, transform: [{ scale: 0.98 }] },
            isLoading && { opacity: 0.5 },
          ]}
          onPress={calculateCompatibility}
          disabled={isLoading || !partnerA || !partnerB}
        >
          <LinearGradient
            colors={isLoading ? ['#333', '#333'] : ['#6366f1', '#ec4899']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.calcGradient}
          >
            {isLoading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Text style={styles.calcIcon}>💫</Text>
                <Text style={styles.calcText}>Calculate Compatibility</Text>
              </>
            )}
          </LinearGradient>
        </Pressable>
      </View>

      {/* Loading state indicator */}
      {isLoading && (
        <View style={styles.loadingCard}>
          <ActivityIndicator size="large" color={colors.accent.indigo} />
          <Text style={styles.loadingText}>Synthesizing charts…</Text>
          <Text style={styles.loadingSubtext}>
            Computing Ashta Kuta compatibility and drafting celestial alignment report. This may take up to a minute.
          </Text>
        </View>
      )}

      {/* ─── Results ─────────────────────────────────────────────────── */}
      {result && (
        <View style={styles.resultsSection}>
          {/* Total Score Ring */}
          <ScoreRing score={result.score} />

          {/* Kuta Breakdown */}
          <Text style={styles.sectionTitle}>Ashta Kuta Breakdown</Text>
          {KUTA_ORDER.map((key) => {
            const kuta = result.breakdown[key];
            if (!kuta) return null;
            const info = KUTA_INFO[key];
            return (
              <KutaBar
                key={key}
                title={info?.title || key}
                icon={info?.icon || '◎'}
                meaning={info?.meaning || ''}
                score={kuta.score}
                max={kuta.max}
                groom={kuta.groom}
                bride={kuta.bride}
                cancelled={kuta.cancelled}
              />
            );
          })}

          {/* Advanced Indicators */}
          {result.advanced_compatibility && (
            <AdvancedIndicators
              advanced={result.advanced_compatibility}
              partnerAName={partnerA?.name || 'A'}
              partnerBName={partnerB?.name || 'B'}
            />
          )}

          {/* Reading */}
          {reading ? (
            <View style={styles.readingCard}>
              <Text style={styles.readingSectionTitle}>Partnership Synthesis</Text>
              {renderAstrologyMarkdown(reading)}
            </View>
          ) : null}
        </View>
      )}

      {/* No profiles warning */}
      {eligibleProfiles.length < 2 && (
        <View style={styles.warningCard}>
          <Text style={styles.warningIcon}>⚠️</Text>
          <Text style={styles.warningTitle}>Need Complete Profiles</Text>
          <Text style={styles.warningText}>
            You need at least 2 profiles with birth date, time, and location to run a compatibility check.
            Go to the Profile tab to set these up.
          </Text>
        </View>
      )}
    </Animated.View>
  );
}

// ── Profile Picker ──────────────────────────────────────────────────────────

function ProfilePicker({
  label,
  selected,
  profiles,
  onSelect,
  color,
}: {
  label: string;
  selected: Profile | null;
  profiles: Profile[];
  onSelect: (p: Profile) => void;
  color: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.pickerCard}>
      <Text style={[styles.pickerLabel, { color }]}>{label}</Text>
      <Pressable
        style={[styles.pickerSelect, { borderColor: color + '44' }]}
        onPress={() => setExpanded(!expanded)}
      >
        <View style={[styles.pickerAvatar, { backgroundColor: color + '22' }]}>
          <Text style={[styles.pickerAvatarText, { color }]}>
            {selected?.name?.charAt(0)?.toUpperCase() || '?'}
          </Text>
        </View>
        <Text style={styles.pickerName} numberOfLines={1}>
          {selected?.name || 'Select…'}
        </Text>
        <Text style={styles.pickerChevron}>{expanded ? '▲' : '▼'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.pickerDropdown}>
          {profiles.map((p) => (
            <Pressable
              key={p.id}
              style={[
                styles.pickerOption,
                selected?.id === p.id && { backgroundColor: color + '15' },
              ]}
              onPress={() => {
                onSelect(p);
                setExpanded(false);
              }}
            >
              <Text style={styles.pickerOptionText}>{p.name}</Text>
              <Text style={styles.pickerOptionMeta}>{p.relation}</Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

// ── Score Ring ───────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const animValue = useRef(new Animated.Value(0)).current;
  const percentage = (score / 36) * 100;

  useEffect(() => {
    Animated.timing(animValue, {
      toValue: 1,
      duration: 1200,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();
  }, [animValue]);

  const getVerdict = (s: number): { label: string; color: string; emoji: string } => {
    if (s >= 28) return { label: 'Exceptional', color: '#10b981', emoji: '💚' };
    if (s >= 21) return { label: 'Very Good',   color: '#6366f1', emoji: '💜' };
    if (s >= 18) return { label: 'Good',        color: '#f59e0b', emoji: '💛' };
    if (s >= 14) return { label: 'Average',     color: '#f97316', emoji: '🧡' };
    return                { label: 'Challenging', color: '#ef4444', emoji: '❤️' };
  };

  const verdict = getVerdict(score);
  const size = 180;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <View style={styles.ringContainer}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.bg.elevated}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Score arc */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={verdict.color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          rotation="-90"
          origin={`${size / 2}, ${size / 2}`}
        />
        {/* Score text */}
        <SvgTextEl
          x={size / 2}
          y={size / 2 - 8}
          textAnchor="middle"
          fill={colors.fg.primary}
          fontSize={36}
          fontWeight="700"
        >
          {score}
        </SvgTextEl>
        <SvgTextEl
          x={size / 2}
          y={size / 2 + 16}
          textAnchor="middle"
          fill={colors.fg.muted}
          fontSize={14}
        >
          out of 36
        </SvgTextEl>
      </Svg>

      <Text style={[styles.verdictText, { color: verdict.color }]}>
        {verdict.emoji} {verdict.label}
      </Text>
      <Text style={styles.verdictSubtext}>
        {percentage.toFixed(0)}% compatibility match
      </Text>
    </View>
  );
}

// ── Kuta Bar ────────────────────────────────────────────────────────────────

function KutaBar({
  title,
  icon,
  meaning,
  score,
  max,
  groom,
  bride,
  cancelled,
}: {
  title: string;
  icon: string;
  meaning: string;
  score: number;
  max: number;
  groom?: string;
  bride?: string;
  cancelled?: boolean;
}) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  const barColor = pct >= 75 ? '#10b981' : pct >= 50 ? '#f59e0b' : pct >= 25 ? '#f97316' : '#ef4444';

  return (
    <View style={styles.kutaCard}>
      <View style={styles.kutaHeader}>
        <Text style={styles.kutaIcon}>{icon}</Text>
        <View style={styles.kutaHeaderText}>
          <Text style={styles.kutaTitle}>{title}</Text>
          <Text style={styles.kutaMeaning}>{meaning}</Text>
        </View>
        <View style={styles.kutaScoreBadge}>
          <Text style={[styles.kutaScoreText, { color: barColor }]}>
            {score}/{max}
          </Text>
        </View>
      </View>

      {/* Bar */}
      <View style={styles.kutaBarTrack}>
        <View style={[styles.kutaBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
      </View>

      {/* Partner labels */}
      {(groom || bride) && (
        <View style={styles.kutaPartners}>
          {groom && (
            <Text style={styles.kutaPartnerText}>A: {groom}</Text>
          )}
          {bride && (
            <Text style={styles.kutaPartnerText}>B: {bride}</Text>
          )}
          {cancelled && (
            <Text style={styles.kutaCancelled}>Dosha cancelled ✓</Text>
          )}
        </View>
      )}
    </View>
  );
}

// ── Advanced Indicators ─────────────────────────────────────────────────────

function AdvancedIndicators({
  advanced,
  partnerAName,
  partnerBName,
}: {
  advanced: AdvancedCompat;
  partnerAName: string;
  partnerBName: string;
}) {
  const kuja = advanced.kuja_dosha;
  const suit = advanced.suitability;

  return (
    <View style={styles.advancedSection}>
      <Text style={styles.sectionTitle}>Advanced Indicators</Text>

      {/* Manglik Status */}
      <View style={[styles.indicatorCard, !kuja.compatible && styles.indicatorWarning]}>
        <View style={styles.indicatorHeader}>
          <Text style={styles.indicatorIcon}>{kuja.compatible ? '✅' : '⚠️'}</Text>
          <Text style={styles.indicatorTitle}>Manglik (Kuja Dosha)</Text>
        </View>
        <Text style={styles.indicatorStatus}>{kuja.status}</Text>
        <View style={styles.indicatorDetails}>
          <Text style={styles.indicatorDetail}>
            {partnerAName}: {kuja.partner_a_manglik ? 'Manglik' : 'Non-Manglik'} — {kuja.partner_a_reason}
          </Text>
          <Text style={styles.indicatorDetail}>
            {partnerBName}: {kuja.partner_b_manglik ? 'Manglik' : 'Non-Manglik'} — {kuja.partner_b_reason}
          </Text>
        </View>
        <Text style={styles.indicatorReason}>{kuja.reason}</Text>
      </View>

      {/* Rajju & Vedha */}
      {(advanced as any).rajju && (
        <View style={[
          styles.indicatorCard,
          (advanced as any).rajju.has_dosha && styles.indicatorWarning,
        ]}>
          <View style={styles.indicatorHeader}>
            <Text style={styles.indicatorIcon}>
              {(advanced as any).rajju.has_dosha ? '⚠️' : '✅'}
            </Text>
            <Text style={styles.indicatorTitle}>Rajju Dosha</Text>
          </View>
          <Text style={styles.indicatorDetail}>
            A: {(advanced as any).rajju.groom} · B: {(advanced as any).rajju.bride}
          </Text>
        </View>
      )}

      {/* Suitability Matrix */}
      {suit && (
        <View style={styles.suitabilityCard}>
          <Text style={styles.suitabilityTitle}>Relationship Suitability</Text>
          <SuitabilityRow label="Romantic / Marriage" value={suit.romantic_marriage} icon="💍" />
          <SuitabilityRow label="Platonic Friendship" value={suit.platonic_friendship} icon="🤝" />
          <SuitabilityRow label="Business / Professional" value={suit.business_professional} icon="💼" />
          <SuitabilityRow label="Mentorship / Growth" value={suit.mentorship_growth} icon="🌱" />
          <View style={styles.bestSuited}>
            <Text style={styles.bestSuitedLabel}>Best suited for:</Text>
            <Text style={styles.bestSuitedValue}>{suit.best_suited}</Text>
          </View>
        </View>
      )}
    </View>
  );
}

function SuitabilityRow({ label, value, icon }: { label: string; value: number; icon: string }) {
  const pct = Math.min(value * 10, 100); // Assuming 0-10 scale
  const barColor = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <View style={styles.suitRow}>
      <Text style={styles.suitIcon}>{icon}</Text>
      <Text style={styles.suitLabel}>{label}</Text>
      <View style={styles.suitBarTrack}>
        <View style={[styles.suitBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
      </View>
      <Text style={[styles.suitValue, { color: barColor }]}>{value}/10</Text>
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
      // Empty line / paragraph spacing
      elements.push(<View key={`space-${keyCounter++}`} style={{ height: spacing.sm }} />);
      continue;
    }

    // 1. Headers
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

    // 2. Bullet list items
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

    // 3. Regular paragraph
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
  container: { paddingTop: spacing.md },

  // Section titles
  sectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.md,
    marginTop: spacing['2xl'],
  },

  // Profile picker
  pickerSection: { marginBottom: spacing.md },
  pickerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  pickerDivider: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: spacing['3xl'],
  },
  vsText: {
    fontFamily: fonts.display,
    fontSize: fontSizes.sm,
    color: colors.fg.faint,
    letterSpacing: 2,
  },
  pickerCard: { flex: 1 },
  pickerLabel: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  pickerSelect: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.glass,
    borderRadius: radii.md,
    borderWidth: 1,
    padding: spacing.md,
    gap: spacing.sm,
  },
  pickerAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickerAvatarText: { fontFamily: fonts.display, fontSize: fontSizes.sm },
  pickerName: {
    flex: 1,
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  pickerChevron: { fontSize: 10, color: colors.fg.faint },
  pickerDropdown: {
    marginTop: spacing.xs,
    backgroundColor: colors.bg.card,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.elevated,
    overflow: 'hidden',
  },
  pickerOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.bg.elevated,
  },
  pickerOptionText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.primary,
  },
  pickerOptionMeta: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.faint,
  },

  // Calculate button
  calcButton: {
    borderRadius: radii.lg,
    overflow: 'hidden',
    marginTop: spacing.xl,
  },
  calcGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.lg,
    borderRadius: radii.lg,
    gap: spacing.sm,
  },
  calcIcon: { fontSize: 18 },
  calcText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: '#fff',
    letterSpacing: 0.3,
  },

  // Results
  resultsSection: { marginTop: spacing.md },

  // Score ring
  ringContainer: {
    alignItems: 'center',
    paddingVertical: spacing['2xl'],
  },
  verdictText: {
    fontFamily: fonts.display,
    fontSize: fontSizes.xl,
    marginTop: spacing.md,
  },
  verdictSubtext: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: spacing.xs,
  },

  // Kuta bars
  kutaCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  kutaHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  kutaIcon: { fontSize: 18, marginRight: spacing.sm },
  kutaHeaderText: { flex: 1 },
  kutaTitle: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  kutaMeaning: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
    marginTop: 1,
  },
  kutaScoreBadge: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
    backgroundColor: colors.bg.card,
  },
  kutaScoreText: {
    fontFamily: fonts.display,
    fontSize: fontSizes.sm,
  },
  kutaBarTrack: {
    height: 6,
    backgroundColor: colors.bg.elevated,
    borderRadius: 3,
    overflow: 'hidden',
  },
  kutaBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  kutaPartners: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  kutaPartnerText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.faint,
  },
  kutaCancelled: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.emerald,
  },

  // Advanced indicators
  advancedSection: { marginTop: spacing.md },
  indicatorCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  indicatorWarning: {
    borderColor: colors.accent.amber + '44',
    backgroundColor: colors.accent.amber + '08',
  },
  indicatorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  indicatorIcon: { fontSize: 18 },
  indicatorTitle: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  indicatorStatus: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    marginBottom: spacing.sm,
  },
  indicatorDetails: { gap: spacing.xs },
  indicatorDetail: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
    lineHeight: 16,
  },
  indicatorReason: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    marginTop: spacing.sm,
    fontStyle: 'italic',
  },

  // Suitability matrix
  suitabilityCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.xl,
    marginBottom: spacing.md,
  },
  suitabilityTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
    marginBottom: spacing.lg,
  },
  suitRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
    gap: spacing.sm,
  },
  suitIcon: { fontSize: 16, width: 24 },
  suitLabel: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.secondary,
    width: 120,
  },
  suitBarTrack: {
    flex: 1,
    height: 4,
    backgroundColor: colors.bg.elevated,
    borderRadius: 2,
    overflow: 'hidden',
  },
  suitBarFill: { height: '100%', borderRadius: 2 },
  suitValue: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    width: 32,
    textAlign: 'right',
  },
  bestSuited: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.bg.elevated,
  },
  bestSuitedLabel: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
  },
  bestSuitedValue: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.accent.indigo,
  },

  // Reading
  readingCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
    marginTop: spacing['2xl'],
  },
  readingSectionTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.md,
  },
  readingText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.secondary,
    lineHeight: 24,
  },

  // Warning
  warningCard: {
    backgroundColor: colors.accent.amber + '10',
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.accent.amber + '33',
    padding: spacing['2xl'],
    alignItems: 'center',
    marginTop: spacing['2xl'],
  },
  warningIcon: { fontSize: 32, marginBottom: spacing.md },
  warningTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.base,
    color: colors.accent.amber,
    marginBottom: spacing.sm,
  },
  warningText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
  },
  loadingCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['2xl'],
    alignItems: 'center',
    marginTop: spacing['2xl'],
    gap: spacing.sm,
  },
  loadingText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
    marginTop: spacing.sm,
  },
  loadingSubtext: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
  },
});
