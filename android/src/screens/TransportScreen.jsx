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
import BookingDatePicker from '../components/BookingDatePicker';
import { TrainIcon, HelicopterIcon, BusIcon, PlaneIcon, InfoIcon } from '../components/Icons';
import { fetchTransportOptions, getCachedTransportOptions } from '../services/api';
import {
  CURATED_FLIGHTS,
  FLIGHT_ORIGIN_PRESETS,
  FLIGHT_DESTINATION_PRESETS,
  filterAndSortFlights,
  deduplicateFlights,
  toBookingTransportOption,
} from '../utils/flightCatalog';

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
  // Multi-Operator Bus Fleets (Government & Private)
  {
    id: 'bus-1',
    mode: 'Bus',
    title: 'JKSRTC Volvo Multi-Axle AC (Delhi–Jammu + Feeder)',
    provider: 'JKRTC / J&K State Transport Authority (Government)',
    origin: 'ISBT Kashmiri Gate, Delhi',
    destination: 'Jammu GBS / Katra Feeder',
    duration: '12h 30m',
    departure: '07:30 PM & 08:30 PM',
    arrival: '08:00 AM & 09:00 AM',
    frequency: 'Daily evening services',
    fareRange: '₹1,250 - ₹1,450',
    stops: 'Murthal, Karnal, Ludhiana, Pathankot, Jammu GBS',
    bookingPlatform: 'jksrtc.co.in / Bus Counters',
    is_verified: false,
    is_partially_verified: true,
  },
  {
    id: 'bus-2',
    mode: 'Bus',
    title: 'Laxmi Holidays Volvo 9600 Multi-Axle AC Sleeper',
    provider: 'Laxmi Holidays (Private Fleet Operator)',
    origin: 'ISBT Kashmiri Gate / Majnu Ka Tila, Delhi',
    destination: 'Subhash Parking, Katra',
    duration: '12h 00m',
    departure: '06:30 PM, 08:30 PM, 10:30 PM',
    arrival: '06:30 AM, 08:30 AM, 10:30 AM',
    frequency: 'Multiple daily overnight departures',
    fareRange: '₹899 - ₹1,550',
    stops: 'ISBT Kashmiri Gate, Majnu Ka Tila, Karnal Bypass, Katra',
    bookingPlatform: 'laxmiholidays.com / redBus',
    is_verified: true,
  },
  {
    id: 'bus-3',
    mode: 'Bus',
    title: 'Zingbus BharatBenz Premium AC Sleeper',
    provider: 'Zingbus (Private Fleet Operator)',
    origin: 'Majnu Ka Tila (Zingbus Lounge), Delhi',
    destination: 'New Bus Stand, Katra',
    duration: '12h 30m',
    departure: '06:45 PM, 07:30 PM, 09:15 PM',
    arrival: '07:15 AM, 08:00 AM, 09:45 AM',
    frequency: 'Daily evening departures with waiting lounge',
    fareRange: '₹649 - ₹1,399',
    stops: 'Majnu Ka Tila Lounge, Kashmiri Gate, Mukarba Chowk, Katra',
    bookingPlatform: 'zingbus.com / Official App',
    is_verified: true,
  },
  {
    id: 'bus-4',
    mode: 'Bus',
    title: 'FlixBus India Economy AC Seater/Sleeper',
    provider: 'FlixBus India (Private Network)',
    origin: 'ISBT Kashmiri Gate, Delhi',
    destination: 'New Bus Stand Parking, Katra',
    duration: '12h 15m',
    departure: '05:25 PM, 06:25 PM, 11:10 PM',
    arrival: '05:45 AM, 06:45 AM, 11:30 AM',
    frequency: 'Daily scheduled line service',
    fareRange: '₹499 - ₹999 (Lowest Indicative Tariff)',
    stops: 'ISBT Kashmiri Gate, Sanjay Gandhi Transport Nagar, Katra',
    bookingPlatform: 'flixbus.in / FlixBus App',
    is_verified: true,
  },
  {
    id: 'bus-5',
    mode: 'Bus',
    title: 'IntrCity SmartBus Premium Sleeper (Washroom Onboard)',
    provider: 'IntrCity SmartBus (Private Fleet Operator)',
    origin: 'Majnu Ka Tila IntrCity Lounge, Delhi',
    destination: 'Bhawani Parking, Katra',
    duration: '12h 30m',
    departure: '04:00 PM, 07:30 PM, 09:30 PM',
    arrival: '04:30 AM, 08:00 AM, 10:00 AM',
    frequency: 'Daily evening departures with private lounge access',
    fareRange: '₹750 - ₹1,450',
    stops: 'Majnu Ka Tila, ISBT Kashmiri Gate, Mukarba Chowk, Katra',
    bookingPlatform: 'intrcity.com / RailYatri',
    is_verified: true,
  },
  {
    id: 'bus-6',
    mode: 'Bus',
    title: 'HRTC Interstate Volvo 9400',
    provider: 'HRTC - Himachal Road Transport Corporation (Government)',
    origin: 'ISBT 43, Chandigarh',
    destination: 'Katra Central Bus Stand',
    duration: '9h 00m',
    departure: '08:30 PM',
    arrival: '05:30 AM',
    frequency: 'Daily overnight service',
    fareRange: '₹950 - ₹1,200',
    stops: 'Chandigarh ISBT 43, Ambala, Pathankot, Jammu, Katra',
    bookingPlatform: 'hrtchp.com / Stand Counters',
    is_verified: true,
  },
  {
    id: 'bus-7',
    mode: 'Bus',
    title: 'PRTC / Punbus Interstate Express',
    provider: 'PRTC / Punjab Roadways (Government)',
    origin: 'Amritsar ISBT',
    destination: 'Katra New Bus Stand',
    duration: '6h 45m',
    departure: '06:15 AM & 08:30 AM',
    arrival: '01:00 PM & 03:15 PM',
    frequency: 'Daily daytime scheduled departures',
    fareRange: '₹380 - ₹520',
    stops: 'Amritsar, Gurdaspur, Pathankot, Jammu, Katra',
    bookingPlatform: 'punbusonline.com / ISBT Counter',
    is_verified: true,
  },
  {
    id: 'bus-8',
    mode: 'Bus',
    title: 'Connecting Route via Jammu General Bus Stand (GBS)',
    provider: 'Interstate Express + JKRTC Feeder Shuttle (Connecting)',
    origin: 'Delhi / Chandigarh / Srinagar',
    destination: 'Katra Central Bus Stand (via Jammu GBS)',
    duration: '~14h 00m (includes 60m transfer buffer)',
    departure: 'Evening departures linking at Jammu (07:30 AM)',
    arrival: 'Katra Central Stand by 09:30 AM',
    frequency: 'High-frequency stage carriages every 15 mins from Jammu',
    fareRange: '₹725 - ₹1,045 (Combined Estimated Tariff)',
    stops: 'Origin Hub → Jammu General Bus Stand (60m buffer) → Katra',
    bookingPlatform: 'jksrtc.co.in / Official Stand Counters',
    is_connecting: true,
    is_verified: false,
    is_partially_verified: true,
  },
];

const INITIAL_CURATED_TRANSPORTS = [...CURATED_TRANSPORTS, ...CURATED_FLIGHTS];

const MODES = ['All', 'Flight', 'Train', 'Helicopter', 'Bus'];
const FLIGHT_STOPS_FILTERS = [
  { id: 'all', label: 'All Stops' },
  { id: 'nonstop', label: 'Non-Stop' },
  { id: 'connecting', label: 'Connecting' },
];
const FLIGHT_SORT_OPTIONS = [
  { id: 'price_asc', label: 'Lowest Price' },
  { id: 'departure_asc', label: 'Earliest Departure' },
  { id: 'duration_asc', label: 'Shortest Duration' },
];

export default function TransportScreen({ navigation }) {
  const [transports, setTransports] = useState(() => {
    const cachedFlights = getCachedTransportOptions();
    if (Array.isArray(cachedFlights) && cachedFlights.length > 0) {
      return [...CURATED_TRANSPORTS, ...deduplicateFlights([...cachedFlights, ...CURATED_FLIGHTS])];
    }
    return INITIAL_CURATED_TRANSPORTS;
  });
  const [selectedMode, setSelectedMode] = useState('All');
  const [flightOrigin, setFlightOrigin] = useState('');
  const [flightDestination, setFlightDestination] = useState('');
  const [flightDate, setFlightDate] = useState('');
  const [stopsFilter, setStopsFilter] = useState('all');
  const [sortBy, setSortBy] = useState('price_asc');
  const [selectedFlightId, setSelectedFlightId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadTransports({ forceRefresh: false });
  }, []);

  // Invalidate selected flight whenever route, date, or stops filter changes
  useEffect(() => {
    setSelectedFlightId(null);
  }, [flightOrigin, flightDestination, flightDate, stopsFilter]);

  const loadTransports = async ({ forceRefresh = false } = {}) => {
    try {
      const data = await fetchTransportOptions({ forceRefresh });
      if (Array.isArray(data) && data.length > 0) {
        const mergedFlights = deduplicateFlights([...data, ...CURATED_FLIGHTS]);
        const nonFlights = CURATED_TRANSPORTS.filter((t) => t.mode !== 'Flight');
        setTransports([...nonFlights, ...mergedFlights]);
      }
    } catch (e) {
      // Keep curated/cached transports
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadTransports({ forceRefresh: true });
  };

  const handleSelectFlightForBooking = (item) => {
    if (!item) return;
    setSelectedFlightId(item.id);
    if (item.mode === 'Flight') {
      const bookingOption = toBookingTransportOption(item);
      navigation.navigate('Booking', {
        selectedTransport: bookingOption,
        origin: item.originCity || flightOrigin || 'Delhi',
        startDate: flightDate || undefined,
        includeTransport: true,
        ownVehicle: false,
        step: 2,
        overrideDraft: true,
      });
    } else {
      navigation.navigate('Booking', {
        includeTransport: true,
        ownVehicle: false,
        step: 2,
      });
    }
  };

  const nonFlightTransports = transports.filter((item) => item.mode !== 'Flight');
  const rawFlights = transports.filter((item) => item.mode === 'Flight');
  const filteredFlights = filterAndSortFlights(rawFlights, {
    origin: flightOrigin,
    destination: flightDestination,
    travelDate: flightDate,
    stopsFilter,
    sortBy,
  });

  const filteredTransports =
    selectedMode === 'Flight'
      ? filteredFlights
      : selectedMode === 'All'
      ? [...nonFlightTransports, ...filteredFlights]
      : nonFlightTransports.filter((item) => item.mode === selectedMode);

  return (
    <View style={styles.container}>
      <Header
        title="Transport Guidance"
        subtitle="Schedules, Fares & Routes"
        showBack={true}
        onBackPress={() => navigation.navigate('Assistant')}
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
          {selectedMode === 'Flight'
            ? 'Curated DGCA/AAI flight corridors & indicative fare bands. Confirm live airfare on airline portals.'
            : 'Schedules are verified reference timings. Confirm live seats on IRCTC / SMVDSB / airline portals.'}
        </Text>
      </View>

      {(selectedMode === 'Flight' || selectedMode === 'All') && (
        <View style={styles.flightFilterPanel}>
          <Text style={styles.flightPanelLabel}>
            Flight Origin ({filteredFlights.length} matching flights)
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
            {FLIGHT_ORIGIN_PRESETS.map((preset) => {
              const active = flightOrigin === preset.value;
              return (
                <TouchableOpacity
                  key={preset.label}
                  style={[styles.filterChip, active && styles.filterChipActive]}
                  onPress={() => setFlightOrigin(preset.value)}
                >
                  <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                    {preset.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={[styles.chipRow, { marginTop: 6 }]}>
            {FLIGHT_DESTINATION_PRESETS.map((dest) => {
              const active = flightDestination === dest.value;
              return (
                <TouchableOpacity
                  key={dest.label}
                  style={[styles.filterChip, active && styles.filterChipActive]}
                  onPress={() => setFlightDestination(dest.value)}
                >
                  <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                    {dest.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
            {FLIGHT_STOPS_FILTERS.map((sf) => {
              const active = stopsFilter === sf.id;
              return (
                <TouchableOpacity
                  key={sf.id}
                  style={[styles.filterChip, active && styles.filterChipActive]}
                  onPress={() => setStopsFilter(sf.id)}
                >
                  <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                    {sf.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={[styles.chipRow, { marginTop: 6 }]}>
            {FLIGHT_SORT_OPTIONS.map((opt) => {
              const active = sortBy === opt.id;
              return (
                <TouchableOpacity
                  key={opt.id}
                  style={[styles.filterChip, active && styles.filterChipActive]}
                  onPress={() => setSortBy(opt.id)}
                >
                  <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                    Sort: {opt.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          {selectedMode === 'Flight' && (
            <View style={{ marginTop: 8 }}>
              <BookingDatePicker
                label="Filter Travel Date (Optional)"
                value={flightDate}
                onChange={setFlightDate}
              />
              {flightDate ? (
                <TouchableOpacity onPress={() => setFlightDate('')} style={{ marginTop: 4 }}>
                  <Text style={styles.clearDateText}>Clear Date Filter ({flightDate})</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          )}
        </View>
      )}

      <FlatList
        data={filteredTransports}
        keyExtractor={(item, idx) => item.id || String(idx)}
        renderItem={({ item }) => (
          <TransportCard
            transport={item}
            selected={selectedFlightId === item.id}
            onSelect={item.mode === 'Flight' ? handleSelectFlightForBooking : undefined}
          />
        )}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyFlightBox}>
            <Text style={styles.emptyFlightTitle}>No matching flight schedules found</Text>
            <Text style={styles.emptyFlightSubtitle}>
              No audited flight corridor matched {flightOrigin || 'selected origin'} → {flightDestination || 'IXJ/SXR'}.
              Try selecting "All" destinations, "All Stops" (for 1-stop DEL connections), or choosing Train/Bus options.
            </Text>
          </View>
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
      />
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
  flightFilterPanel: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  flightPanelLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 6,
  },
  chipRow: {
    gap: 6,
    paddingRight: 12,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  filterChipActive: {
    backgroundColor: colors.burgundy,
    borderColor: colors.burgundy,
  },
  filterChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text,
  },
  filterChipTextActive: {
    color: '#F4E5BE',
    fontWeight: '700',
  },
  clearDateText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
  },
  emptyFlightBox: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    padding: 16,
    alignItems: 'center',
  },
  emptyFlightTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.burgundy,
    marginBottom: 6,
  },
  emptyFlightSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 17,
  },
});
