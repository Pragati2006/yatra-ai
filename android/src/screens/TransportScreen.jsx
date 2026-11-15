import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import TransportCard from '../components/TransportCard';
import { TrainIcon, HelicopterIcon, BusIcon, PlaneIcon, InfoIcon } from '../components/Icons';
import { fetchTransportOptions } from '../services/api';

const CURATED_TRANSPORTS = [
  // Trains
  {
    id: 'train-1',
    mode: 'Train',
    title: 'Vande Bharat Express (22439 / 22440)',
    origin: 'New Delhi (NDLS)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '8h 00m',
    departure: '06:00 AM (NDLS)',
    arrival: '02:00 PM (SVDK)',
    frequency: 'All days except Tuesday',
    fareRange: '₹1,630 (CC) - ₹3,015 (EC)',
    stops: 'Ambala Cantt, Ludhiana, Jammu Tawi',
    bookingPlatform: 'IRCTC / PRS Counters',
  },
  {
    id: 'train-2',
    mode: 'Train',
    title: 'Uttar Sampark Kranti (12445 / 12446)',
    origin: 'New Delhi (NDLS)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '11h 40m',
    departure: '08:50 PM (NDLS)',
    arrival: '08:05 AM (SVDK)',
    frequency: 'Daily Overnight',
    fareRange: '₹375 (SL) - ₹1,430 (3A) - ₹2,050 (2A)',
    stops: 'Panipat, Ambala, Ludhiana, Jammu Tawi, Udhampur',
    bookingPlatform: 'IRCTC / PRS Counters',
  },
  {
    id: 'train-3',
    mode: 'Train',
    title: 'Hemkunt Express (14609 / 14610)',
    origin: 'Rishikesh (RKSH)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '14h 50m',
    departure: '05:20 PM (RKSH)',
    arrival: '08:10 AM (SVDK)',
    frequency: 'Daily',
    fareRange: '₹390 (SL) - ₹1,080 (3A) - ₹1,550 (2A)',
    stops: 'Haridwar, Saharanpur, Ambala, Jammu Tawi',
    bookingPlatform: 'IRCTC / PRS Counters',
  },
  // Helicopter
  {
    id: 'heli-1',
    mode: 'Helicopter',
    title: 'Shrine Board Aerial Shuttle',
    origin: 'Katra Helipad (875m)',
    destination: 'Sanjichhat Helipad (1,768m)',
    duration: '8 minutes flight',
    departure: 'Continuous daylight flights',
    arrival: 'Operates 07:00 AM - 05:00 PM',
    frequency: 'Every 10-15 minutes (weather permitting)',
    fareRange: '₹2,100 (One Way) / ₹4,200 (Return)',
    stops: 'Direct aerial corridor over Banganga gorge',
    bookingPlatform: 'maavaishnodevi.org (Official portal only)',
  },
  // Bus
  {
    id: 'bus-1',
    mode: 'Bus',
    title: 'JKSRTC Volvo Multi-Axle AC',
    origin: 'ISBT Kashmiri Gate, Delhi',
    destination: 'Katra Bus Stand',
    duration: '12h 30m',
    departure: '07:30 PM & 08:30 PM',
    arrival: '08:00 AM & 09:00 AM',
    frequency: 'Daily evening services',
    fareRange: '₹1,250 - ₹1,650',
    stops: 'Murthal, Karnal, Ludhiana, Pathankot, Jammu',
    bookingPlatform: 'jksrtc.co.in / Bus Counters',
  },
  // Flight
  {
    id: 'flight-1',
    mode: 'Flight',
    title: 'Direct Flight to Jammu Airport (IXJ)',
    origin: 'Delhi / Mumbai / Bengaluru',
    destination: 'Jammu Civil Enclave (IXJ)',
    duration: '1h 25m (from DEL)',
    departure: 'Multiple daily departures',
    arrival: 'Katra is 48 km by direct pre-paid taxi (1h 15m)',
    frequency: 'Operated by IndiGo, Air India, SpiceJet',
    fareRange: '₹3,500 - ₹7,500 (dynamic flight fare)',
    stops: 'Direct nonstop flight + Jammu-Katra highway taxi',
    bookingPlatform: 'Airlines / Travel aggregators',
  },
];

const MODES = ['All', 'Train', 'Helicopter', 'Bus', 'Flight'];

export default function TransportScreen({ navigation }) {
  const [transports, setTransports] = useState(CURATED_TRANSPORTS);
  const [selectedMode, setSelectedMode] = useState('All');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadTransports();
  }, []);

  const loadTransports = async () => {
    setLoading(true);
    try {
      const data = await fetchTransportOptions();
      if (Array.isArray(data) && data.length > 0) {
        setTransports(data);
      }
    } catch (e) {
      // Keep curated transports
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadTransports();
  };

  const filteredTransports = transports.filter(
    (item) => selectedMode === 'All' || item.mode === selectedMode
  );

  return (
    <View style={styles.container}>
      <Header
        title="Transport Guidance"
        subtitle="Schedules, Fares & Routes"
      />

      <View style={styles.tabBar}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabContent}>
          {MODES.map((mode) => (
            <TouchableOpacity
              key={mode}
              style={[
                styles.tabBtn,
                selectedMode === mode && styles.tabBtnActive,
              ]}
              onPress={() => setSelectedMode(mode)}
            >
              <View style={styles.tabInner}>
                {mode === 'Train' && <TrainIcon size={13} color={selectedMode === mode ? colors.surface : colors.primary} />}
                {mode === 'Helicopter' && <HelicopterIcon size={13} color={selectedMode === mode ? colors.surface : colors.primary} />}
                {mode === 'Bus' && <BusIcon size={13} color={selectedMode === mode ? colors.surface : colors.primary} />}
                {mode === 'Flight' && <PlaneIcon size={13} color={selectedMode === mode ? colors.surface : colors.primary} />}
                <Text
                  style={[
                    styles.tabText,
                    selectedMode === mode && styles.tabTextActive,
                    mode !== 'All' && { marginLeft: 5 },
                  ]}
                >
                  {mode}
                </Text>
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <View style={styles.disclaimerBar}>
        <InfoIcon size={13} color="#92400E" />
        <Text style={styles.disclaimerText}>
          Schedules are verified reference timings. Book tickets via official IRCTC / SMVDSB portals.
        </Text>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading verified transport schedules...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredTransports}
          keyExtractor={(item, idx) => item.id || String(idx)}
          renderItem={({ item }) => <TransportCard transport={item} />}
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
  tabBar: {
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    ...spacing.shadowSm,
  },
  tabContent: {
    paddingHorizontal: spacing.md,
    gap: spacing.xs,
  },
  tabBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: spacing.radiusSm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  tabBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
  },
  tabTextActive: {
    color: colors.surface,
    fontWeight: '700',
  },
  tabInner: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  disclaimerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#F59E0B',
    gap: 6,
  },
  disclaimerText: {
    fontSize: 11,
    color: '#92400E',
    fontWeight: '500',
  },
  listContent: {
    padding: spacing.md,
    gap: spacing.md,
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
