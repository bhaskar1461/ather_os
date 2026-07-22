/**
 * Register Screen — account creation with celestial theming.
 *
 * Mirrors the login screen's design language but adds a name field
 * and password confirmation.
 */

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Animated,
  Alert,
} from 'react-native';
import { Link, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthStore } from '../../src/store/useAuthStore';
import { colors, fonts, fontSizes, spacing, radii } from '../../src/theme/tokens';

export default function RegisterScreen() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const { register, isLoading } = useAuthStore();
  const router = useRouter();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  React.useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const handleRegister = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Missing Fields', 'Please fill in all required fields.');
      return;
    }
    if (password !== confirmPassword) {
      Alert.alert('Password Mismatch', 'Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      Alert.alert('Weak Password', 'Password must be at least 6 characters.');
      return;
    }

    try {
      await register(email.trim(), password, name.trim() || undefined);
      router.replace('/(tabs)/cosmos');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      Alert.alert('Registration Failed', message);
    }
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#050507', '#0a0a1a', '#0d0d2b', '#050507']}
        locations={[0, 0.3, 0.6, 1]}
        style={StyleSheet.absoluteFill}
      />

      <View style={styles.glowOrb} />

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Animated.View
            style={[
              styles.content,
              { opacity: fadeAnim, transform: [{ translateY: slideAnim }] },
            ]}
          >
            {/* Brand */}
            <View style={styles.brandSection}>
              <Text style={styles.brandIcon}>✦</Text>
              <Text style={styles.brandTitle}>Join AetherOS</Text>
              <Text style={styles.brandSubtitle}>Begin your cosmic journey</Text>
            </View>

            {/* Form Card */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Create Account</Text>
              <Text style={styles.cardSubtitle}>
                Set up your profile to unlock personalized readings
              </Text>

              {/* Name */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Name (optional)</Text>
                <TextInput
                  style={styles.input}
                  value={name}
                  onChangeText={setName}
                  placeholder="Your name"
                  placeholderTextColor={colors.fg.faint}
                  autoCapitalize="words"
                  editable={!isLoading}
                />
              </View>

              {/* Email */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Email</Text>
                <TextInput
                  style={styles.input}
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@example.com"
                  placeholderTextColor={colors.fg.faint}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  editable={!isLoading}
                />
              </View>

              {/* Password */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Password</Text>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  placeholder="At least 6 characters"
                  placeholderTextColor={colors.fg.faint}
                  secureTextEntry
                  autoComplete="new-password"
                  editable={!isLoading}
                />
              </View>

              {/* Confirm Password */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Confirm Password</Text>
                <TextInput
                  style={styles.input}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  placeholder="Repeat password"
                  placeholderTextColor={colors.fg.faint}
                  secureTextEntry
                  editable={!isLoading}
                />
              </View>

              {/* Register Button */}
              <Pressable
                style={({ pressed }) => [
                  styles.primaryButton,
                  pressed && styles.primaryButtonPressed,
                  isLoading && styles.primaryButtonDisabled,
                ]}
                onPress={handleRegister}
                disabled={isLoading}
              >
                <LinearGradient
                  colors={
                    isLoading
                      ? ['#333', '#333']
                      : ['#6366f1', '#8b5cf6']
                  }
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.buttonGradient}
                >
                  <Text style={styles.primaryButtonText}>
                    {isLoading ? 'Creating account…' : 'Create Account'}
                  </Text>
                </LinearGradient>
              </Pressable>

              {/* Login link */}
              <View style={styles.linkRow}>
                <Text style={styles.linkText}>Already have an account? </Text>
                <Link href="/(auth)/login" asChild>
                  <Pressable>
                    <Text style={styles.linkAction}>Sign in</Text>
                  </Pressable>
                </Link>
              </View>
            </View>
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.deep },
  keyboardView: { flex: 1 },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing['3xl'],
  },
  content: { alignItems: 'center' },
  glowOrb: {
    position: 'absolute',
    top: '10%',
    right: '15%',
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(139, 92, 246, 0.07)',
    transform: [{ scale: 2 }],
  },
  brandSection: { alignItems: 'center', marginBottom: spacing['3xl'] },
  brandIcon: { fontSize: 44, color: colors.accent.violet, marginBottom: spacing.md },
  brandTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes['2xl'],
    color: colors.fg.primary,
    letterSpacing: -1,
  },
  brandSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginTop: spacing.xs,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  card: {
    width: '100%',
    backgroundColor: colors.bg.glass,
    borderRadius: radii.xl,
    borderWidth: 1,
    borderColor: colors.bg.glassBorder,
    padding: spacing['3xl'],
  },
  cardTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes.xl,
    color: colors.fg.primary,
    marginBottom: spacing.xs,
  },
  cardSubtitle: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
    marginBottom: spacing['2xl'],
  },
  inputGroup: { marginBottom: spacing.lg },
  inputLabel: {
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
  primaryButton: {
    borderRadius: radii.md,
    overflow: 'hidden',
    marginTop: spacing.md,
  },
  primaryButtonPressed: { opacity: 0.85, transform: [{ scale: 0.98 }] },
  primaryButtonDisabled: { opacity: 0.5 },
  buttonGradient: {
    paddingVertical: spacing.lg,
    alignItems: 'center',
    borderRadius: radii.md,
  },
  primaryButtonText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: '#fff',
    letterSpacing: 0.3,
  },
  linkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: spacing['2xl'],
  },
  linkText: { fontFamily: fonts.body, fontSize: fontSizes.sm, color: colors.fg.muted },
  linkAction: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.accent.indigo,
  },
});
