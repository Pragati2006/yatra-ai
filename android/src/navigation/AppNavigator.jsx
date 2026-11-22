import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { colors } from '../theme/colors';
import {
  MessageSquareIcon,
  MountainIcon,
  TrainIcon,
  CloudSunIcon,
  TicketIcon,
  BuildingIcon,
  SettingsIcon,
} from '../components/Icons';

// Screens
import SplashScreen from '../screens/SplashScreen';
import ChatScreen from '../screens/ChatScreen';
import HistoryScreen from '../screens/HistoryScreen';
import AuthScreen from '../screens/AuthScreen';
import TourismScreen from '../screens/TourismScreen';
import TransportScreen from '../screens/TransportScreen';
import WeatherScreen from '../screens/WeatherScreen';
import AccommodationScreen from '../screens/AccommodationScreen';
import BookingScreen from '../screens/BookingScreen';
import SettingsScreen from '../screens/SettingsScreen';
import ItineraryScreen from '../screens/ItineraryScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function TabIcon({ focused, IconComponent, label }) {
  const iconColor = focused ? colors.primary : colors.textSecondary;
  return (
    <View style={styles.tabItem}>
      <View style={[styles.tabIconWrapper, focused && styles.tabIconFocused]}>
        <IconComponent size={20} color={iconColor} strokeWidth={focused ? 2.3 : 1.8} />
      </View>
      <Text style={[styles.tabLabelText, focused && styles.tabLabelFocused]}>{label}</Text>
    </View>
  );
}

function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { display: 'none' },
        tabBarShowLabel: false,
      }}
    >
      <Tab.Screen
        name="Assistant"
        component={ChatScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={MessageSquareIcon} label="Assistant" />
          ),
        }}
      />
      <Tab.Screen
        name="Destinations"
        component={TourismScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={MountainIcon} label="Holy Sites" />
          ),
        }}
      />
      <Tab.Screen
        name="Transport"
        component={TransportScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={TrainIcon} label="Transport" />
          ),
        }}
      />
      <Tab.Screen
        name="Weather"
        component={WeatherScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={CloudSunIcon} label="Weather" />
          ),
        }}
      />
      <Tab.Screen
        name="Booking"
        component={BookingScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={TicketIcon} label="Booking" />
          ),
        }}
      />
      <Tab.Screen
        name="Stay"
        component={AccommodationScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={BuildingIcon} label="Bhawans" />
          ),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon focused={focused} IconComponent={SettingsIcon} label="Settings" />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Splash"
        screenOptions={{
          headerShown: false,
          animation: 'fade',
        }}
      >
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="MainTabs" component={MainTabNavigator} />
        <Stack.Screen
          name="Auth"
          component={AuthScreen}
          options={{ animation: 'slide_from_right' }}
        />
        <Stack.Screen
          name="History"
          component={HistoryScreen}
          options={{ animation: 'slide_from_right' }}
        />
        <Stack.Screen
          name="Itinerary"
          component={ItineraryScreen}
          options={{ animation: 'slide_from_right' }}
        />
        <Stack.Screen
          name="Accommodation"
          component={AccommodationScreen}
          options={{ animation: 'slide_from_right' }}
        />
        <Stack.Screen
          name="SettingsModal"
          component={SettingsScreen}
          options={{ animation: 'slide_from_bottom' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.goldBorder,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
  },
  tabItem: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  tabIconWrapper: {
    marginBottom: 2,
    opacity: 0.85,
  },
  tabIconFocused: {
    opacity: 1,
    transform: [{ scale: 1.05 }],
  },
  tabLabelText: {
    fontSize: 9.5,
    fontWeight: '600',
    color: colors.textSecondary,
    letterSpacing: 0.2,
  },
  tabLabelFocused: {
    color: colors.primary,
    fontWeight: '800',
  },
});
