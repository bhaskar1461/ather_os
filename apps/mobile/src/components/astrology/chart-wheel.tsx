/**
 * Chart Wheel — North Indian diamond-style Vedic birth chart.
 *
 * Port of apps/web/src/components/astrology/chart-wheel.tsx
 * using react-native-svg instead of DOM SVG elements.
 *
 * Features:
 *  - 12 house diamond layout with the same coordinate system
 *  - Planet symbols positioned within houses
 *  - Tap-to-reveal house tooltip (replaces web hover)
 *  - Animated entrance: houses draw in sequence
 */

import React, { useState, useEffect, useRef } from 'react';
import { View, Text, Pressable, StyleSheet, Animated } from 'react-native';
import { Svg, Polygon, Line, G, Text as SvgText } from 'react-native-svg';
import { colors, fonts, fontSizes, spacing, radii } from '../../theme/tokens';

// ── Types ───────────────────────────────────────────────────────────────────

interface PlanetData {
  longitude?: number;
  speed?: number;
  is_retrograde?: boolean;
  sign: string;
  sign_index: number;
  degrees: number;
  house: number;
}

interface AscendantData {
  longitude?: number;
  sign: string;
  sign_index: number;
  degrees?: number;
}

interface ChartWheelProps {
  planets: Record<string, PlanetData>;
  ascendant: AscendantData;
  size?: number;
}

// ── Constants (from web chart-wheel.tsx) ─────────────────────────────────────

const PLANET_SYMBOLS: Record<string, string> = {
  sun: 'Su',
  moon: 'Mo',
  mars: 'Ma',
  mercury: 'Me',
  jupiter: 'Ju',
  venus: 'Ve',
  saturn: 'Sa',
  rahu: 'Ra',
  ketu: 'Ke',
};

const SIGN_SYMBOLS = [
  'Ar', 'Ta', 'Ge', 'Cn', 'Le', 'Vi',
  'Li', 'Sc', 'Sg', 'Cp', 'Aq', 'Pi',
];

const HOUSE_COORDS = [
  { house: 1,  signX: 200, signY: 135, planetsX: 200, planetsY: 90,
    tooltip: '1st House (Lagna): Self, personality, vital energy',
    points: '200,200 100,100 200,0 300,100' },
  { house: 2,  signX: 110, signY: 85,  planetsX: 95,  planetsY: 55,
    tooltip: '2nd House: Wealth, family, speech, values',
    points: '0,0 200,0 100,100' },
  { house: 3,  signX: 85,  signY: 110, planetsX: 55,  planetsY: 95,
    tooltip: '3rd House: Courage, siblings, communication',
    points: '0,0 100,100 0,200' },
  { house: 4,  signX: 135, signY: 200, planetsX: 90,  planetsY: 200,
    tooltip: '4th House: Mother, home, emotions, vehicles',
    points: '0,200 100,100 200,200 100,300' },
  { house: 5,  signX: 85,  signY: 290, planetsX: 55,  planetsY: 305,
    tooltip: '5th House: Children, intelligence, creativity',
    points: '0,200 100,300 0,400' },
  { house: 6,  signX: 110, signY: 315, planetsX: 95,  planetsY: 345,
    tooltip: '6th House: Health, obstacles, debts, service',
    points: '0,400 100,300 200,400' },
  { house: 7,  signX: 200, signY: 265, planetsX: 200, planetsY: 310,
    tooltip: '7th House: Spouse, partnerships, trade',
    points: '200,200 100,300 200,400 300,300' },
  { house: 8,  signX: 290, signY: 315, planetsX: 305, planetsY: 345,
    tooltip: '8th House: Longevity, transformation, hidden things',
    points: '200,400 300,300 400,400' },
  { house: 9,  signX: 315, signY: 290, planetsX: 345, planetsY: 305,
    tooltip: '9th House: Fortune, dharma, higher learning',
    points: '400,400 300,300 400,200' },
  { house: 10, signX: 265, signY: 200, planetsX: 310, planetsY: 200,
    tooltip: '10th House: Career, status, public image',
    points: '200,200 300,300 400,200 300,100' },
  { house: 11, signX: 315, signY: 110, planetsX: 345, planetsY: 95,
    tooltip: '11th House: Gains, income, social networks',
    points: '400,200 300,100 400,0' },
  { house: 12, signX: 290, signY: 85,  planetsX: 305, planetsY: 55,
    tooltip: '12th House: Losses, spirituality, foreign lands',
    points: '400,0 200,0 300,100' },
];

// ── Component ───────────────────────────────────────────────────────────────

export default function ChartWheel({ planets, ascendant, size = 340 }: ChartWheelProps) {
  const [selectedHouse, setSelectedHouse] = useState<number | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 1000,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  const scale = size / 400;

  // Build house → sign mapping based on ascendant
  const ascSignIdx = ascendant.sign_index ?? 0;
  const houseToSign = Array.from({ length: 12 }, (_, i) => (ascSignIdx + i) % 12);

  // Build house → planets mapping
  const housePlanets: Record<number, { symbol: string; retrograde: boolean }[]> = {};
  Object.entries(planets).forEach(([name, data]) => {
    const h = data.house;
    if (!housePlanets[h]) housePlanets[h] = [];
    housePlanets[h].push({
      symbol: PLANET_SYMBOLS[name] || name.slice(0, 2),
      retrograde: data.is_retrograde || false,
    });
  });

  const selectedCoord = selectedHouse !== null
    ? HOUSE_COORDS.find((h) => h.house === selectedHouse)
    : null;

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      <View style={[styles.chartWrapper, { width: size, height: size }]}>
        <Svg width={size} height={size} viewBox="0 0 400 400">
          {/* Outer border */}
          <Polygon
            points="200,0 400,200 200,400 0,200"
            fill="none"
            stroke={colors.chart.houseBorder}
            strokeWidth={1.5}
          />

          {/* Inner diamond (house dividers) */}
          <Polygon
            points="100,100 300,100 300,300 100,300"
            fill="none"
            stroke={colors.chart.houseBorder}
            strokeWidth={0.8}
          />

          {/* Cross lines */}
          <Line x1="200" y1="0" x2="200" y2="400" stroke={colors.chart.houseBorder} strokeWidth={0.8} />
          <Line x1="0" y1="200" x2="400" y2="200" stroke={colors.chart.houseBorder} strokeWidth={0.8} />

          {/* Diagonal connectors */}
          <Line x1="100" y1="100" x2="0" y2="0" stroke={colors.chart.houseBorder} strokeWidth={0.8} />
          <Line x1="300" y1="100" x2="400" y2="0" stroke={colors.chart.houseBorder} strokeWidth={0.8} />
          <Line x1="300" y1="300" x2="400" y2="400" stroke={colors.chart.houseBorder} strokeWidth={0.8} />
          <Line x1="100" y1="300" x2="0" y2="400" stroke={colors.chart.houseBorder} strokeWidth={0.8} />

          {/* House touch targets + sign labels */}
          {HOUSE_COORDS.map((coord) => {
            const signIdx = houseToSign[coord.house - 1];
            const isSelected = selectedHouse === coord.house;

            return (
              <G key={coord.house}>
                {/* Touch target polygon */}
                <Polygon
                  points={coord.points}
                  fill={isSelected ? colors.chart.houseActive : 'transparent'}
                  onPress={() =>
                    setSelectedHouse(isSelected ? null : coord.house)
                  }
                />

                {/* Sign abbreviation */}
                <SvgText
                  x={coord.signX}
                  y={coord.signY}
                  textAnchor="middle"
                  fill={colors.fg.faint}
                  fontSize={11}
                  fontWeight="500"
                >
                  {SIGN_SYMBOLS[signIdx]}
                </SvgText>

                {/* Planet symbols */}
                {(housePlanets[coord.house] || []).map((p, i) => (
                  <SvgText
                    key={`${coord.house}-${p.symbol}`}
                    x={coord.planetsX + (i % 3) * 22 - 18}
                    y={coord.planetsY + Math.floor(i / 3) * 16}
                    textAnchor="middle"
                    fill={p.retrograde ? colors.accent.rose : colors.accent.amber}
                    fontSize={12}
                    fontWeight="700"
                  >
                    {p.symbol}{p.retrograde ? '®' : ''}
                  </SvgText>
                ))}
              </G>
            );
          })}

          {/* ASC label in center */}
          <SvgText
            x="200"
            y="203"
            textAnchor="middle"
            fill={colors.accent.indigo}
            fontSize={13}
            fontWeight="700"
          >
            ASC: {ascendant.sign?.slice(0, 3)}
          </SvgText>
        </Svg>
      </View>

      {/* Tooltip */}
      {selectedCoord && (
        <View style={styles.tooltip}>
          <Text style={styles.tooltipTitle}>
            House {selectedCoord.house} · {SIGN_SYMBOLS[houseToSign[selectedCoord.house - 1]]}
          </Text>
          <Text style={styles.tooltipText}>{selectedCoord.tooltip}</Text>
          {housePlanets[selectedCoord.house]?.map((p) => (
            <Text key={p.symbol} style={styles.tooltipPlanet}>
              {p.symbol} {p.retrograde ? '(Retrograde)' : ''}
            </Text>
          ))}
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  chartWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  tooltip: {
    marginTop: spacing.md,
    backgroundColor: colors.bg.glass,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.lg,
    width: '100%',
  },
  tooltipTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.base,
    color: colors.accent.indigo,
    marginBottom: spacing.xs,
  },
  tooltipText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    lineHeight: 18,
  },
  tooltipPlanet: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.accent.amber,
    marginTop: spacing.xs,
  },
});
