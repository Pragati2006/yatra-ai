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
import HotelCard from '../components/HotelCard';
import { fetchAccommodations } from '../services/api';

const CURATED_ACCOMMODATIONS = [
  {
    id: 'smvdsb-niharika',
    name: 'Niharika Complex (SMVDSB)',
    type: 'Shrine Board',
    location: 'Near Bus Stand, Katra (Base)',
    tariff: '₹800 - ₹2,100 / night',
    distance: '0.2 km from Katra Bus Stand | 1.8 km to Banganga',
    rating: 4.5,
    amenities: ['Pure Veg Bhojanalaya', 'Locker Facility', 'Yatra Registration Counter', '24h Hot Water'],
    inventoryNote: 'Reserved directly via Shrine Board portal. High demand.',
    officialLink: 'maavaishnodevi.org',
  },
  {
    id: 'smvdsb-shakti',
    name: 'Shakti Bhawan (SMVDSB)',
    type: 'Shrine Board',
    location: 'Holy Cave Bhawan Complex (Sanctum)',
    tariff: '₹1,100 - ₹2,800 / night',
    distance: '0.1 km from Holy Cave Sanctum',
    rating: 4.6,
    amenities: ['Warm Bedding', 'Electric Blankets', 'Hot Water', 'Direct Sanctum Access'],
    inventoryNote: 'Strictly allocated for senior citizens and pre-booked yatris.',
    officialLink: 'maavaishnodevi.org',
  },
  {
    id: 'smvdsb-ardhkuwari',
    name: 'Ardhkuwari Rest House (SMVDSB)',
    type: 'Shrine Board',
    location: 'Garbhjoon Temple Compound (Mid-Trek)',
    tariff: '₹600 - ₹1,400 / night',
    distance: '6 km from Katra | 6.5 km to Bhawan',
    rating: 4.2,
    amenities: ['Dormitory Beds', 'Blanket Service', 'Free Luggage Room', 'Bhojanalaya'],
    inventoryNote: 'Ideal for resting during long Garbhjoon darshan token waits.',
    officialLink: 'maavaishnodevi.org',
  },
  {
    id: 'hotel-the-white',
    name: 'The White Hotel Katra',
    type: 'Luxury / Star',
    location: 'Railway Road, Katra',
    tariff: '₹4,500 - ₹8,500 / night',
    distance: '1 km from Railway Station | 2.5 km to Banganga',
    rating: 4.7,
    amenities: ['5-Star Luxury', 'Pure Vegetarian Restaurant', 'Helipad Shuttle', 'Spa & Wellness'],
    inventoryNote: 'Premium stay with private panoramic Trikuta mountain view.',
    officialLink: 'Direct Hotel Booking',
  },
  {
    id: 'hotel-hari-niwas',
    name: 'Hotel Shree Hari Niwas',
    type: 'Budget',
    location: 'Jammu Road, Katra',
    tariff: '₹1,200 - ₹2,200 / night',
    distance: '0.5 km from Bus Stand | 2 km to Banganga',
    rating: 4.1,
    amenities: ['Free WiFi', 'AC Rooms', 'Room Service', 'Banganga Drop Assistance'],
    inventoryNote: 'Devotee-friendly family budget accommodation.',
    officialLink: 'Direct Booking',
  },
];

const CATEGORIES = ['All', 'Shrine Board', 'Budget', 'Luxury / Star'];

export default function AccommodationScreen({ navigation }) {
  const [accommodations, setAccommodations] = useState(CURATED_ACCOMMODATIONS);
  const [selectedCat, setSelectedCat] = useState('All');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAccommodations();
  }, []);

  const loadAccommodations = async () => {
    setLoading(true);
    try {
      const data = await fetchAccommodations();
      if (Array.isArray(data) && data.length > 0) {
        setAccommodations(data);
      }
    } catch (e) {
      // Keep curated list
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadAccommodations();
  };

  const handleSelectHotel = (hotel) => {
    navigation.navigate('Booking', { initialHotel: hotel.name });
  };

  const filteredAccommodations = accommodations.filter(
    (item) => selectedCat === 'All' || item.type === selectedCat
  );

  return (
    <View style={styles.container}>
      <Header
        title="Pilgrim Accommodation"
        subtitle="Bhawans, Ashrams & Hotels"
      />

      <View style={styles.filterBar}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterContent}>
          {CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[
                styles.filterBtn,
                selectedCat === cat && styles.filterBtnActive,
              ]}
              onPress={() => setSelectedCat(cat)}
            >
              <Text
                style={[
                  styles.filterText,
                  selectedCat === cat && styles.filterTextActive,
                ]}
              >
                {cat}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <View style={styles.noticeBar}>
        <Text style={styles.noticeText}>
          Shrine Board Bhawan bookings open exactly 60 days in advance on maavaishnodevi.org. Beware of unofficial fraudulent websites.
        </Text>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Fetching accommodation catalog...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredAccommodations}
          keyExtractor={(item, idx) => item.id || String(idx)}
          renderItem={({ item }) => (
            <HotelCard hotel={item} onSelect={() => handleSelectHotel(item)} />
          )}
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
  filterBar: {
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    ...spacing.shadowSm,
  },
  filterContent: {
    paddingHorizontal: spacing.md,
    gap: spacing.xs,
  },
  filterBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: spacing.radiusSm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  filterBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
  },
  filterTextActive: {
    color: colors.surface,
    fontWeight: '700',
  },
  noticeBar: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderBottomWidth: 1,
    borderBottomColor: '#F59E0B',
  },
  noticeText: {
    fontSize: 11,
    color: '#92400E',
    lineHeight: 15,
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
