import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import {
  CloudRainIcon,
  SnowIcon,
  CloudSunIcon,
  SunIcon,
  MountainIcon,
} from './Icons';

export default function WeatherCard({ data }) {
  if (!data) return null;

  const renderWeatherIcon = (condition) => {
    const c = (condition || '').toLowerCase();
    if (c.includes('rain') || c.includes('shower')) return <CloudRainIcon size={24} color={colors.primary} />;
    if (c.includes('snow') || c.includes('frost')) return <SnowIcon size={24} color={colors.primary} />;
    if (c.includes('cloud') || c.includes('overcast')) return <CloudSunIcon size={24} color={colors.primary} />;
    if (c.includes('clear') || c.includes('sun')) return <SunIcon size={24} color={colors.gold} />;
    return <MountainIcon size={24} color={colors.primary} />;
  };

  const title = data.locationName || data.location || 'Katra Base Camp';
  const altitude = data.altitude || data.elevation || '875m (2,870 ft)';
  const tempDrop = data.tempDrop || null;

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.titleContainer}>
          <Text style={styles.locationTitle}>{title}</Text>
          <View style={styles.altitudeRow}>
            <Text style={styles.altitudeTag}>Elevation: {altitude}</Text>
            {tempDrop && <Text style={styles.tempDropTag}>{tempDrop}</Text>}
          </View>
        </View>
        <View style={styles.weatherIconBox}>{renderWeatherIcon(data.condition || data.weather)}</View>
      </View>

      <View style={styles.tempRow}>
        <Text style={styles.tempText}>{data.temperature !== undefined ? `${data.temperature}°C` : '18°C'}</Text>
        <View style={styles.conditionBox}>
          <Text style={styles.conditionText}>{data.condition || data.weather || 'Pleasant & Clear'}</Text>
          {data.feels_like && <Text style={styles.feelsLike}>Feels like {data.feels_like}°C</Text>}
          {data.humidity !== undefined && (
            <Text style={styles.metricsText}>
              Humidity: {data.humidity}% | Wind: {data.windSpeed || data.wind_speed || 8} km/h
            </Text>
          )}
        </View>
      </View>

      {/* Advisory & Metadata */}
      {data.advisory && (
        <View style={styles.advisoryBox}>
          <Text style={styles.advisoryLabel}>Pilgrim Advisory:</Text>
          <Text style={styles.advisoryText}>{data.advisory}</Text>
        </View>
      )}

      <View style={styles.sourceRow}>
        <Text style={styles.sourceText}>
          Source: {data.source || 'Open-Meteo Microclimate Elevation API'}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: 14,
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
    padding: 14,
    marginBottom: 12,
    shadowColor: '#58111A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  titleContainer: {
    flex: 1,
    marginRight: 8,
  },
  locationTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.burgundy,
  },
  altitudeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
    flexWrap: 'wrap',
  },
  altitudeTag: {
    fontSize: 11,
    color: colors.goldDark,
    fontWeight: '700',
  },
  tempDropTag: {
    fontSize: 10,
    color: colors.burgundy,
    backgroundColor: colors.goldSubtle,
    paddingVertical: 1,
    paddingHorizontal: 6,
    borderRadius: 4,
    fontWeight: '700',
  },
  weatherIconBox: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: colors.goldSubtle,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tempRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 6,
  },
  tempText: {
    fontSize: 32,
    fontWeight: '800',
    color: colors.burgundy,
    marginRight: 12,
  },
  conditionBox: {
    justifyContent: 'center',
    flex: 1,
  },
  conditionText: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  feelsLike: {
    fontSize: 11.5,
    color: colors.textMuted,
  },
  metricsText: {
    fontSize: 10.5,
    color: colors.textSecondary,
    marginTop: 2,
  },
  advisoryBox: {
    backgroundColor: colors.goldSubtle,
    borderRadius: 8,
    padding: 8,
    marginTop: 6,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  advisoryLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.burgundy,
  },
  advisoryText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 16,
  },
  sourceRow: {
    marginTop: 8,
    alignItems: 'flex-end',
  },
  sourceText: {
    fontSize: 9.5,
    color: colors.textMuted,
    fontStyle: 'italic',
  },
});
