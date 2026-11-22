import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import WeatherCard from '../components/WeatherCard';
import { MountainIcon } from '../components/Icons';
import { fetchWeather } from '../services/api';

const ELEVATION_ZONES = [
  {
    location: 'katra',
    locationName: 'Katra (Base Camp)',
    altitude: '875 m (2,870 ft)',
    condition: 'Partly Cloudy',
    temperature: 24,
    humidity: 55,
    windSpeed: 8,
    precipitationProb: 10,
    advisory: 'Pleasant daytime conditions. Standard walking shoes recommended for start of trek.',
    tempDrop: 'Baseline Temperature',
  },
  {
    location: 'ardhkuwari',
    locationName: 'Ardhkuwari (Mid-Trek)',
    altitude: '1,460 m (4,790 ft)',
    condition: 'Cool Breeze',
    temperature: 19,
    humidity: 62,
    windSpeed: 14,
    precipitationProb: 20,
    advisory: 'Noticeable drop in temperature (~5°C lower than Katra). Light windcheater advised.',
    tempDrop: '-5.0°C vs Katra Base',
  },
  {
    location: 'vaishno_devi_bhawan',
    locationName: 'Holy Cave Bhawan',
    altitude: '1,585 m (5,200 ft)',
    condition: 'Chilly & Overcast',
    temperature: 15,
    humidity: 68,
    windSpeed: 18,
    precipitationProb: 25,
    advisory: 'Brisk mountain winds. Warm jacket or woolen shawl required, especially during evening Aarti.',
    tempDrop: '-8.5°C vs Katra Base',
  },
  {
    location: 'bhairon_temple',
    locationName: 'Bhairon Ghati (Peak)',
    altitude: '2,012 m (6,600 ft)',
    condition: 'Cold & Windy',
    temperature: 11,
    humidity: 75,
    windSpeed: 24,
    precipitationProb: 35,
    advisory: 'High altitude chill. Heavy woollens and gloves recommended. Watch out for sudden fog patches.',
    tempDrop: '-13.0°C vs Katra Base',
  },
];

export default function WeatherScreen({ navigation }) {
  const [weatherData, setWeatherData] = useState(ELEVATION_ZONES);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadLiveWeather();
  }, []);

  const loadLiveWeather = async () => {
    setLoading(true);
    try {
      const updated = await Promise.all(
        ELEVATION_ZONES.map(async (zone) => {
          try {
            const live = await fetchWeather(zone.location);
            if (live && live.temperature !== undefined) {
              return {
                ...zone,
                temperature: Math.round(live.temperature),
                condition: live.condition || live.weather_code_desc || zone.condition,
                humidity: live.humidity || zone.humidity,
                windSpeed: live.wind_speed || zone.windSpeed,
                precipitationProb: live.precipitation_prob || zone.precipitationProb,
                advisory: live.advisory || zone.advisory,
              };
            }
          } catch (e) {
            // Keep fallback
          }
          return zone;
        })
      );
      setWeatherData(updated);
    } catch (e) {
      // Use defaults
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadLiveWeather();
  };

  return (
    <View style={styles.container}>
      <Header
        title="Microclimate & Weather"
        subtitle="Elevation-Aware Pilgrim Advisory"
        showBack={true}
        onBackPress={() => navigation.navigate('Assistant')}
      />

      <View style={styles.elevationInfoBanner}>
        <View style={styles.bannerIconContainer}>
          <MountainIcon size={24} color={colors.primary} />
        </View>
        <View style={styles.bannerTextContainer}>
          <Text style={styles.bannerTitle}>Atmospheric Lapse Rate Warning</Text>
          <Text style={styles.bannerDescription}>
            Temperature drops by ~6.5°C for every 1,000m of ascent. Katra base is often warm while Bhawan and Bhairon summit experience bitter cold winds.
          </Text>
        </View>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Sampling Open-Meteo elevation stations...</Text>
        </View>
      ) : (
        <FlatList
          data={weatherData}
          keyExtractor={(item) => item.location}
          renderItem={({ item }) => <WeatherCard data={item} />}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              colors={[colors.primary]}
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  elevationInfoBanner: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceSecondary,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    padding: spacing.md,
    alignItems: 'center',
    ...spacing.shadowSm,
  },
  bannerIconContainer: {
    marginRight: spacing.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  bannerIcon: {
    fontSize: 26,
    marginRight: spacing.sm,
  },
  bannerTextContainer: {
    flex: 1,
  },
  bannerTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 2,
  },
  bannerDescription: {
    fontSize: 11,
    color: colors.textSecondary,
    lineHeight: 15,
  },
  listContent: {
    padding: spacing.md,
    gap: spacing.md,
    paddingBottom: 40,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.sm,
    color: colors.textSecondary,
    fontSize: 13,
  },
});
