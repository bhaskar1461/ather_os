/**
 * Tab Layout — 3-tab bottom navigation: Cosmos, Chat, Profile
 *
 * Uses a custom tab bar with glassmorphism styling that matches
 * the celestial design language.
 */

import React from 'react';
import { Text, StyleSheet, Platform } from 'react-native';
import { Tabs } from 'expo-router';
import { colors, fontSizes, spacing } from '../../src/theme/tokens';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: colors.accent.indigo,
        tabBarInactiveTintColor: colors.fg.muted,
        tabBarLabelStyle: styles.tabLabel,
      }}
    >
      <Tabs.Screen
        name="cosmos"
        options={{
          title: 'Cosmos',
          tabBarIcon: ({ color }) => (
            <Text style={[styles.tabIcon, { color }]}>✦</Text>
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color }) => (
            <Text style={[styles.tabIcon, { color }]}>◉</Text>
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => (
            <Text style={[styles.tabIcon, { color }]}>◎</Text>
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: 'rgba(5, 5, 7, 0.92)',
    borderTopColor: colors.bg.elevated,
    borderTopWidth: StyleSheet.hairlineWidth,
    height: Platform.OS === 'ios' ? 88 : 64,
    paddingTop: spacing.sm,
    paddingBottom: Platform.OS === 'ios' ? 28 : spacing.sm,
    elevation: 0,
  },
  tabIcon: {
    fontSize: 22,
    marginBottom: 2,
  },
  tabLabel: {
    fontSize: fontSizes.xs,
    letterSpacing: 0.3,
  },
});
