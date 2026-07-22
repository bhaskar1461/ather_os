/**
 * Profile Screen — birth profile CRUD with geocoding autocomplete.
 *
 * Features:
 *  - List of birth profiles with selection indicator
 *  - Swipe-to-delete (via long-press for cross-platform)
 *  - Inline profile creation/edit form
 *  - Birth place autocomplete using GET /location/search
 *  - Timezone auto-resolution using GET /location/timezone
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  StyleSheet,
  Alert,
  Modal,
  ScrollView,
  ActivityIndicator,
  Animated,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthStore } from '../../src/store/useAuthStore';
import { useProfileStore, Profile } from '../../src/store/useProfileStore';
import { apiFetch } from '../../src/lib/api-client';
import { colors, fonts, fontSizes, spacing, radii } from '../../src/theme/tokens';

interface LocationResult {
  city: string;
  name?: string;
  state?: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

const RELATION_OPTIONS = ['Self', 'Partner', 'Child', 'Parent', 'Friend', 'Other'];

export default function ProfileScreen() {
  const [formVisible, setFormVisible] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const {
    profiles, selectedProfileId, isLoading,
    fetchProfiles, setSelectedProfileId, addProfile, updateProfile, deleteProfile,
  } = useProfileStore();
  const { user, logout } = useAuthStore();
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    fetchProfiles();
    Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
  }, [fadeAnim, fetchProfiles]);

  const handleDelete = (id: string, name: string) => {
    Alert.alert('Delete Profile?', `Remove "${name}" permanently?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => deleteProfile(id) },
    ]);
  };

  const openEdit = (profile: Profile) => {
    setEditingProfile(profile);
    setFormVisible(true);
  };

  const openCreate = () => {
    setEditingProfile(null);
    setFormVisible(true);
  };

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
              <Text style={styles.headerTitle}>Profiles</Text>
              <Text style={styles.headerSubtitle}>
                {user?.email || 'Manage your birth profiles'}
              </Text>
            </View>
            <Pressable
              style={({ pressed }) => [styles.logoutBtn, pressed && { opacity: 0.7 }]}
              onPress={() => {
                Alert.alert('Sign Out?', 'You will need to log in again.', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Sign Out', style: 'destructive', onPress: logout },
                ]);
              }}
            >
              <Text style={styles.logoutText}>Sign Out</Text>
            </Pressable>
          </View>

          {/* Profile List */}
          {isLoading ? (
            <View style={styles.loadingState}>
              <ActivityIndicator size="large" color={colors.accent.indigo} />
            </View>
          ) : profiles.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>◎</Text>
              <Text style={styles.emptyTitle}>No Profiles Yet</Text>
              <Text style={styles.emptyText}>
                Create a birth profile to generate your personalized cosmic readings
              </Text>
            </View>
          ) : (
            <FlatList
              data={profiles}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.listContent}
              renderItem={({ item }) => (
                <Pressable
                  style={({ pressed }) => [
                    styles.profileCard,
                    selectedProfileId === item.id && styles.profileCardSelected,
                    pressed && { opacity: 0.85 },
                  ]}
                  onPress={() => setSelectedProfileId(item.id)}
                  onLongPress={() => handleDelete(item.id, item.name)}
                >
                  <View style={styles.profileCardHeader}>
                    <View style={styles.profileIcon}>
                      <Text style={styles.profileIconText}>
                        {item.name?.charAt(0)?.toUpperCase() || '?'}
                      </Text>
                    </View>
                    <View style={styles.profileInfo}>
                      <Text style={styles.profileName}>{item.name}</Text>
                      <Text style={styles.profileRelation}>{item.relation}</Text>
                    </View>
                    {selectedProfileId === item.id && (
                      <Text style={styles.selectedBadge}>Active</Text>
                    )}
                  </View>

                  {/* Birth details */}
                  <View style={styles.profileDetails}>
                    {item.birthDate && (
                      <View style={styles.detailRow}>
                        <Text style={styles.detailLabel}>Born</Text>
                        <Text style={styles.detailValue}>
                          {item.birthDate}{item.birthTime ? ` at ${item.birthTime}` : ''}
                        </Text>
                      </View>
                    )}
                    {item.birthPlace && (
                      <View style={styles.detailRow}>
                        <Text style={styles.detailLabel}>Place</Text>
                        <Text style={styles.detailValue}>{item.birthPlace}</Text>
                      </View>
                    )}
                  </View>

                  {/* Edit button */}
                  <Pressable
                    style={styles.editBtn}
                    onPress={() => openEdit(item)}
                  >
                    <Text style={styles.editBtnText}>Edit</Text>
                  </Pressable>
                </Pressable>
              )}
            />
          )}

          {/* FAB */}
          <Pressable
            style={({ pressed }) => [
              styles.fab,
              pressed && { transform: [{ scale: 0.92 }] },
            ]}
            onPress={openCreate}
          >
            <LinearGradient
              colors={['#6366f1', '#8b5cf6']}
              style={styles.fabGradient}
            >
              <Text style={styles.fabIcon}>+</Text>
            </LinearGradient>
          </Pressable>
        </Animated.View>
      </SafeAreaView>

      {/* Profile Form Modal */}
      <ProfileFormModal
        visible={formVisible}
        onClose={() => setFormVisible(false)}
        profile={editingProfile}
        onSave={async (data) => {
          if (editingProfile) {
            await updateProfile(editingProfile.id, data);
          } else {
            await addProfile({ ...data, isDefault: profiles.length === 0 });
          }
          setFormVisible(false);
        }}
      />
    </View>
  );
}

// ── Profile Form Modal ──────────────────────────────────────────────────────

function ProfileFormModal({
  visible,
  onClose,
  profile,
  onSave,
}: {
  visible: boolean;
  onClose: () => void;
  profile: Profile | null;
  onSave: (data: Omit<Profile, 'id' | 'isDefault'>) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [relation, setRelation] = useState('Self');
  const [birthDate, setBirthDate] = useState('');
  const [birthTime, setBirthTime] = useState('');
  const [birthPlace, setBirthPlace] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>();
  const [longitude, setLongitude] = useState<number | undefined>();
  const [timezone, setTimezone] = useState<string | undefined>();
  const [locationResults, setLocationResults] = useState<LocationResult[]>([]);
  const [searchingLocation, setSearchingLocation] = useState(false);
  const [saving, setSaving] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (profile) {
      setName(profile.name || '');
      setRelation(profile.relation || 'Self');
      setBirthDate(profile.birthDate || '');
      setBirthTime(profile.birthTime || '');
      setBirthPlace(profile.birthPlace || '');
      setLatitude(profile.latitude);
      setLongitude(profile.longitude);
      setTimezone(profile.timezone);
    } else {
      setName('');
      setRelation('Self');
      setBirthDate('');
      setBirthTime('');
      setBirthPlace('');
      setLatitude(undefined);
      setLongitude(undefined);
      setTimezone(undefined);
    }
    setLocationResults([]);
  }, [profile, visible]);

  const searchLocation = useCallback((query: string) => {
    setBirthPlace(query);
    setLatitude(undefined);
    setLongitude(undefined);
    setTimezone(undefined);

    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (query.length < 2) {
      setLocationResults([]);
      return;
    }

    searchTimeout.current = setTimeout(async () => {
      setSearchingLocation(true);
      try {
        const data = await apiFetch<{
          results: LocationResult[];
        }>(`/location/search?q=${encodeURIComponent(query)}&limit=5`);
        setLocationResults(data.results || []);
      } catch {
        setLocationResults([]);
      } finally {
        setSearchingLocation(false);
      }
    }, 400);
  }, []);

  const selectLocation = (loc: LocationResult) => {
    const cityName = loc.city || loc.name || '';
    setBirthPlace(`${cityName}${loc.state ? `, ${loc.state}` : ''}, ${loc.country}`);
    setLatitude(loc.latitude);
    setLongitude(loc.longitude);
    setTimezone(loc.timezone);
    setLocationResults([]);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Missing Name', 'Please enter a name for this profile.');
      return;
    }

    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        relation,
        birthDate,
        birthTime,
        birthPlace,
        latitude,
        longitude,
        timezone,
      });
    } catch (err) {
      Alert.alert('Error', 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={formStyles.modal}>
        <SafeAreaView style={formStyles.safeArea}>
          <ScrollView
            contentContainerStyle={formStyles.scrollContent}
            keyboardShouldPersistTaps="handled"
          >
            {/* Header */}
            <View style={formStyles.header}>
              <Pressable onPress={onClose}>
                <Text style={formStyles.cancelText}>Cancel</Text>
              </Pressable>
              <Text style={formStyles.headerTitle}>
                {profile ? 'Edit Profile' : 'New Profile'}
              </Text>
              <Pressable onPress={handleSave} disabled={saving}>
                <Text style={[formStyles.saveText, saving && { opacity: 0.4 }]}>
                  {saving ? 'Saving…' : 'Save'}
                </Text>
              </Pressable>
            </View>

            {/* Name */}
            <View style={formStyles.field}>
              <Text style={formStyles.label}>Name *</Text>
              <TextInput
                style={formStyles.input}
                value={name}
                onChangeText={setName}
                placeholder="e.g. John Doe"
                placeholderTextColor={colors.fg.faint}
                autoCapitalize="words"
              />
            </View>

            {/* Relation */}
            <View style={formStyles.field}>
              <Text style={formStyles.label}>Relation</Text>
              <View style={formStyles.chipRow}>
                {RELATION_OPTIONS.map((opt) => (
                  <Pressable
                    key={opt}
                    style={[
                      formStyles.chip,
                      relation === opt && formStyles.chipActive,
                    ]}
                    onPress={() => setRelation(opt)}
                  >
                    <Text
                      style={[
                        formStyles.chipText,
                        relation === opt && formStyles.chipTextActive,
                      ]}
                    >
                      {opt}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>

            {/* Birth Date */}
            <View style={formStyles.field}>
              <Text style={formStyles.label}>Birth Date</Text>
              <TextInput
                style={formStyles.input}
                value={birthDate}
                onChangeText={setBirthDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.fg.faint}
                keyboardType="numbers-and-punctuation"
              />
            </View>

            {/* Birth Time */}
            <View style={formStyles.field}>
              <Text style={formStyles.label}>Birth Time</Text>
              <TextInput
                style={formStyles.input}
                value={birthTime}
                onChangeText={setBirthTime}
                placeholder="HH:MM (24-hour)"
                placeholderTextColor={colors.fg.faint}
                keyboardType="numbers-and-punctuation"
              />
            </View>

            {/* Birth Place (with autocomplete) */}
            <View style={formStyles.field}>
              <Text style={formStyles.label}>Birth Place</Text>
              <TextInput
                style={formStyles.input}
                value={birthPlace}
                onChangeText={searchLocation}
                placeholder="Start typing a city name…"
                placeholderTextColor={colors.fg.faint}
              />

              {searchingLocation && (
                <ActivityIndicator
                  size="small"
                  color={colors.accent.indigo}
                  style={formStyles.searchSpinner}
                />
              )}

              {/* Location suggestions */}
              {locationResults.length > 0 && (
                <View style={formStyles.suggestions}>
                  {locationResults.map((loc, i) => (
                    <Pressable
                      key={`${loc.latitude}-${loc.longitude}-${i}`}
                      style={({ pressed }) => [
                        formStyles.suggestion,
                        pressed && { backgroundColor: colors.bg.elevated },
                      ]}
                      onPress={() => selectLocation(loc)}
                    >
                      <Text style={formStyles.suggestionName}>
                        {loc.city || loc.name}{loc.state ? `, ${loc.state}` : ''}
                      </Text>
                      <Text style={formStyles.suggestionCountry}>{loc.country}</Text>
                    </Pressable>
                  ))}
                </View>
              )}

              {/* Resolved coords */}
              {latitude !== undefined && longitude !== undefined && (
                <View style={formStyles.resolvedRow}>
                  <Text style={formStyles.resolvedText}>
                    📍 {latitude.toFixed(4)}, {longitude.toFixed(4)}
                    {timezone ? ` · ${timezone}` : ''}
                  </Text>
                </View>
              )}
            </View>
          </ScrollView>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

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
  logoutBtn: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.accent.roseMuted,
  },
  logoutText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.accent.rose,
  },

  loadingState: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing['4xl'],
  },
  emptyIcon: { fontSize: 48, color: colors.fg.faint, marginBottom: spacing.lg },
  emptyTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    textAlign: 'center',
    lineHeight: 20,
  },

  listContent: { paddingHorizontal: spacing['2xl'], paddingBottom: 120 },
  profileCard: {
    backgroundColor: colors.bg.glass,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing.xl,
    marginBottom: spacing.md,
  },
  profileCardSelected: {
    borderColor: colors.accent.indigo,
    backgroundColor: colors.accent.indigoMuted,
  },
  profileCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  profileIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.bg.elevated,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  profileIconText: {
    fontFamily: fonts.display,
    fontSize: fontSizes.md,
    color: colors.fg.primary,
  },
  profileInfo: { flex: 1 },
  profileName: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  profileRelation: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.muted,
    marginTop: 1,
  },
  selectedBadge: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.xs,
    color: colors.accent.indigo,
    backgroundColor: colors.accent.indigoMuted,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.full,
    overflow: 'hidden',
  },
  profileDetails: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.bg.elevated,
  },
  detailRow: {
    flexDirection: 'row',
    marginBottom: spacing.xs,
  },
  detailLabel: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.faint,
    width: 50,
  },
  detailValue: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    flex: 1,
  },
  editBtn: {
    marginTop: spacing.md,
    alignSelf: 'flex-end',
  },
  editBtnText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.accent.indigo,
  },

  fab: {
    position: 'absolute',
    right: spacing['2xl'],
    bottom: spacing['2xl'],
    borderRadius: 28,
    overflow: 'hidden',
  },
  fabGradient: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fabIcon: {
    fontSize: 28,
    color: '#fff',
    fontWeight: '300',
    marginTop: -2,
  },
});

const formStyles = StyleSheet.create({
  modal: { flex: 1, backgroundColor: colors.bg.deep },
  safeArea: { flex: 1 },
  scrollContent: { padding: spacing['2xl'] },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing['3xl'],
    paddingTop: spacing.md,
  },
  cancelText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.base,
    color: colors.fg.muted,
  },
  headerTitle: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
  },
  saveText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.accent.indigo,
  },
  field: { marginBottom: spacing['2xl'] },
  label: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.secondary,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.elevated,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontFamily: fonts.body,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.bg.elevated,
  },
  chipActive: {
    backgroundColor: colors.accent.indigoMuted,
    borderColor: colors.accent.indigo,
  },
  chipText: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
  },
  chipTextActive: {
    color: colors.accent.indigo,
  },
  searchSpinner: { marginTop: spacing.sm },
  suggestions: {
    marginTop: spacing.sm,
    backgroundColor: colors.bg.card,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.bg.elevated,
    overflow: 'hidden',
  },
  suggestion: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.bg.elevated,
  },
  suggestionName: {
    fontFamily: fonts.bodyMedium,
    fontSize: fontSizes.base,
    color: colors.fg.primary,
  },
  suggestionCountry: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.fg.faint,
    marginTop: 2,
  },
  resolvedRow: {
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.accent.emeraldMuted,
    borderRadius: radii.sm,
  },
  resolvedText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.xs,
    color: colors.accent.emerald,
  },
});
