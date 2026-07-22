/**
 * Login Screen — celestial-themed authentication.
 *
 * Features:
 *  - Animated gradient background with subtle star field
 *  - Glassmorphic card for the form
 *  - Email + password fields with validation
 *  - Loading state during API call
 *  - Link to register screen
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

export default function LoginScreen() {
  const [email, setEmail] = useState('admin123@gmail.com');
  const [password, setPassword] = useState('ad1234');
  const [showPassword, setShowPassword] = useState(false);
  const { login, isLoading } = useAuthStore();
  const router = useRouter();

  // Subtle entrance animation
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

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Missing Fields', 'Please enter both email and password.');
      return;
    }

    try {
      await login(email.trim(), password);
      router.replace('/(tabs)/cosmos');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      Alert.alert('Login Failed', message);
    }
  };

  return (
    <View style={styles.container}>
      {/* Background gradient */}
      <LinearGradient
        colors={['#050507', '#0a0a1a', '#0d0d2b', '#050507']}
        locations={[0, 0.3, 0.6, 1]}
        style={StyleSheet.absoluteFill}
      />

      {/* Decorative glow */}
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
            {/* Logo / Brand */}
            <View style={styles.brandSection}>
              <Text style={styles.brandIcon}>✦</Text>
              <Text style={styles.brandTitle}>AetherOS</Text>
              <Text style={styles.brandSubtitle}>Cosmic Intelligence Platform</Text>
            </View>

            {/* Form Card */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Welcome Back</Text>
              <Text style={styles.cardSubtitle}>
                Sign in to access your cosmic readings
              </Text>

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
                <View style={styles.passwordRow}>
                  <TextInput
                    style={[styles.input, styles.passwordInput]}
                    value={password}
                    onChangeText={setPassword}
                    placeholder="••••••••"
                    placeholderTextColor={colors.fg.faint}
                    secureTextEntry={!showPassword}
                    autoComplete="password"
                    editable={!isLoading}
                  />
                  <Pressable
                    onPress={() => setShowPassword(!showPassword)}
                    style={styles.eyeButton}
                  >
                    <Text style={styles.eyeIcon}>
                      {showPassword ? '◉' : '◎'}
                    </Text>
                  </Pressable>
                </View>
              </View>

              {/* Login Button */}
              <Pressable
                style={({ pressed }) => [
                  styles.primaryButton,
                  pressed && styles.primaryButtonPressed,
                  isLoading && styles.primaryButtonDisabled,
                ]}
                onPress={handleLogin}
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
                    {isLoading ? 'Signing in…' : 'Sign In'}
                  </Text>
                </LinearGradient>
              </Pressable>

              {/* Register link */}
              <View style={styles.linkRow}>
                <Text style={styles.linkText}>Don't have an account? </Text>
                <Link href="/(auth)/register" asChild>
                  <Pressable>
                    <Text style={styles.linkAction}>Create one</Text>
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
  container: {
    flex: 1,
    backgroundColor: colors.bg.deep,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing['4xl'],
  },
  content: {
    alignItems: 'center',
  },
  glowOrb: {
    position: 'absolute',
    top: '15%',
    left: '25%',
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(99, 102, 241, 0.08)',
    // Use transform for blur-like effect on RN
    transform: [{ scale: 2 }],
  },
  brandSection: {
    alignItems: 'center',
    marginBottom: spacing['4xl'],
  },
  brandIcon: {
    fontSize: 48,
    color: colors.accent.indigo,
    marginBottom: spacing.md,
  },
  brandTitle: {
    fontFamily: fonts.display,
    fontSize: fontSizes['3xl'],
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
    marginBottom: spacing['3xl'],
  },
  inputGroup: {
    marginBottom: spacing.xl,
  },
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
  passwordRow: {
    position: 'relative',
  },
  passwordInput: {
    paddingRight: 50,
  },
  eyeButton: {
    position: 'absolute',
    right: spacing.lg,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  eyeIcon: {
    fontSize: 20,
    color: colors.fg.muted,
  },
  primaryButton: {
    borderRadius: radii.md,
    overflow: 'hidden',
    marginTop: spacing.md,
  },
  primaryButtonPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  primaryButtonDisabled: {
    opacity: 0.5,
  },
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
  linkText: {
    fontFamily: fonts.body,
    fontSize: fontSizes.sm,
    color: colors.fg.muted,
  },
  linkAction: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.sm,
    color: colors.accent.indigo,
  },
});
