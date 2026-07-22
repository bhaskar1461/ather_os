/**
 * Auth Group Layout — simple stack for login/register screens.
 * No tab bar, no header. Full-screen dark background.
 */

import { Stack } from 'expo-router';
import { colors } from '../../src/theme/tokens';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bg.deep },
        animation: 'fade',
      }}
    />
  );
}
