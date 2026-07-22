import { Stack, useRouter } from 'expo-router';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, fonts, fontSizes, spacing, radii } from '../src/theme/tokens';

export default function NotFoundScreen() {
  const router = useRouter();

  return (
    <>
      <Stack.Screen options={{ title: 'Not Found' }} />
      <View style={styles.container}>
        <Text style={styles.icon}>✦</Text>
        <Text style={styles.title}>This screen doesn't exist</Text>
        <Pressable
          style={({ pressed }) => [styles.link, pressed && { opacity: 0.7 }]}
          onPress={() => router.replace('/(tabs)/cosmos')}
        >
          <Text style={styles.linkText}>Go to Cosmos</Text>
        </Pressable>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg.deep,
    padding: spacing['3xl'],
  },
  icon: { fontSize: 48, color: colors.fg.faint, marginBottom: spacing.lg },
  title: {
    fontFamily: fonts.displayMedium,
    fontSize: fontSizes.lg,
    color: colors.fg.primary,
    marginBottom: spacing['2xl'],
  },
  link: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.accent.indigoMuted,
  },
  linkText: {
    fontFamily: fonts.bodySemibold,
    fontSize: fontSizes.base,
    color: colors.accent.indigo,
  },
});
