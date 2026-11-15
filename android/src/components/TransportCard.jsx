import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import {
  TrainIcon,
  BusIcon,
  PlaneIcon,
  HelicopterIcon,
  CarIcon,
} from './Icons';

export default function TransportCard({ item, transport }) {
  const data = item || transport || {};

  const renderIcon = (mode) => {
    switch ((mode || '').toLowerCase()) {
      case 'train':
        return <TrainIcon size={20} color={colors.primary} />;
      case 'bus':
        return <BusIcon size={20} color={colors.primary} />;
      case 'flight':
        return <PlaneIcon size={20} color={colors.primary} />;
      case 'helicopter':
        return <HelicopterIcon size={20} color={colors.primary} />;
      default:
        return <CarIcon size={20} color={colors.primary} />;
    }
  };

  const title = data.name || data.title || 'Transport Service';
  const subtitle = data.number ? `#${data.number}` : (data.provider || data.mode);
  const departure = data.departure || data.from_station || 'Origin';
  const arrival = data.arrival || data.to_station || 'SVDK / Katra';
  const duration = data.duration || 'Direct Route';
  const frequency = data.frequency || data.days_of_run || 'Daily Pilgrimage Service';
  const fare = data.fare || data.fareRange || null;

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.modeRow}>
          <View style={styles.iconBox}>{renderIcon(data.mode)}</View>
          <View style={styles.titleContainer}>
            <Text style={styles.title} numberOfLines={1}>{title}</Text>
            <Text style={styles.subtitle}>{subtitle}</Text>
          </View>
        </View>

        <View style={styles.badge}>
          <Text style={styles.badgeText}>
            {data.is_connecting ? 'Connecting Route' : (data.is_verified !== false ? 'Verified Schedule' : 'Estimated')}
          </Text>
        </View>
      </View>

      {/* Schedule Info */}
      <View style={styles.scheduleBox}>
        <View style={styles.scheduleItem}>
          <Text style={styles.scheduleLabel}>Departure</Text>
          <Text style={styles.scheduleVal}>{departure}</Text>
          {data.departure_time && <Text style={styles.timeVal}>{data.departure_time}</Text>}
        </View>

        <View style={styles.durationBox}>
          <Text style={styles.durationText}>{duration}</Text>
          <Text style={styles.arrowLine}>────────►</Text>
        </View>

        <View style={styles.scheduleItem}>
          <Text style={styles.scheduleLabel}>Arrival</Text>
          <Text style={styles.scheduleVal}>{arrival}</Text>
          {data.arrival_time && <Text style={styles.timeVal}>{data.arrival_time}</Text>}
        </View>
      </View>

      {/* Connecting Legs List */}
      {Array.isArray(data.legs) && data.legs.length > 0 && (
        <View style={styles.legsBox}>
          <Text style={styles.legsHeader}>
            Connecting Route ({data.legs.length} Legs via {data.primary_hub || 'Hub'}):
          </Text>
          {data.legs.map((leg, idx) => (
            <View key={idx} style={styles.legRow}>
              <Text style={styles.legNumber}>{leg.leg_number || idx + 1}</Text>
              <Text style={styles.legRoute} numberOfLines={1}>
                {leg.from_place} to {leg.to_place} ({leg.mode})
              </Text>
              <Text style={styles.legStatus}>
                {leg.verification_status === 'VERIFIED_SCHEDULE' ? 'Verified' : 'Connecting'}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Fare & Days of Run */}
      <View style={styles.bottomRow}>
        <Text style={styles.daysText} numberOfLines={1}>
          {frequency}
        </Text>
        {fare && (
          <Text style={styles.fareText}>
            {typeof fare === 'number' ? `₹${fare}` : fare}
          </Text>
        )}
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
    alignItems: 'center',
    marginBottom: 10,
  },
  modeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 6,
  },
  titleContainer: {
    flex: 1,
  },
  iconBox: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: colors.goldSubtle,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  title: {
    fontSize: 15,
    fontWeight: '800',
    color: colors.burgundy,
  },
  subtitle: {
    fontSize: 11.5,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  badge: {
    backgroundColor: colors.goldSubtle,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.burgundy,
  },
  scheduleBox: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.bgSubtle,
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  scheduleItem: {
    flex: 1,
    alignItems: 'center',
  },
  scheduleLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
  },
  scheduleVal: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.burgundy,
    marginTop: 2,
    textAlign: 'center',
  },
  timeVal: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 1,
  },
  durationBox: {
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  durationText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.gold,
  },
  arrowLine: {
    fontSize: 10,
    color: colors.goldBorder,
    marginTop: 1,
  },
  bottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  daysText: {
    fontSize: 11.5,
    color: colors.textMuted,
    fontWeight: '500',
    flex: 1,
  },
  fareText: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.burgundy,
    marginLeft: 6,
  },
  legsBox: {
    backgroundColor: '#FFFDF9',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderStyle: 'dashed',
    padding: 8,
    marginBottom: 8,
  },
  legsHeader: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.burgundy,
    marginBottom: 4,
  },
  legRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 2,
  },
  legNumber: {
    fontSize: 9,
    fontWeight: '800',
    color: '#FFF',
    backgroundColor: colors.burgundy,
    borderRadius: 8,
    width: 14,
    height: 14,
    textAlign: 'center',
    lineHeight: 14,
    marginRight: 6,
  },
  legRoute: {
    fontSize: 10.5,
    color: colors.textPrimary,
    flex: 1,
    marginRight: 4,
  },
  legStatus: {
    fontSize: 9,
    fontWeight: '700',
    color: '#2E7D32',
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 3,
  },
});
