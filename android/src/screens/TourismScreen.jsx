import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import TourismCard from '../components/TourismCard';
import { fetchTourismSpots } from '../services/api';

const CURATED_DESTINATIONS = [
  {
    id: 'bhawan',
    name: 'Holy Cave Bhawan (Mata Vaishno Devi)',
    category: 'Sacred Sanctum',
    altitude: '1,585 m (5,200 ft)',
    description:
      'The supreme sanctum sanctorum where the divine Mother resides as three natural rock formations (Pindies): Maha Kali, Maha Lakshmi, and Maha Saraswati.',
    significance: 'Primary darshan objective of the entire 13 km pilgrimage.',
    timings: 'Open 24 hours (Closed during Aarti: 06:00-08:00 AM & 06:00-08:00 PM)',
    darshanTips: 'Lockers, bathing ghats, and Prasad counters available at Bhawan complex.',
  },
  {
    id: 'ardhkuwari',
    name: 'Garbhjoon Cave (Ardhkuwari)',
    category: 'Mid Trek Milestone',
    altitude: '1,460 m (4,800 ft)',
    description:
      'The sacred womb cave where Mata Vaishno Devi meditated in penance for 9 months before manifesting at the Holy Cave.',
    significance: 'Traditional belief states passing through the Garbhjoon cave liberates the soul.',
    timings: 'Continuous tokens distributed; waiting times typically range 6-18 hours.',
    darshanTips: 'Get token registered immediately upon reaching Ardhkuwari before resting.',
  },
  {
    id: 'bhairon',
    name: 'Bhairon Baba Temple',
    category: 'Completing Darshan',
    altitude: '2,012 m (6,600 ft)',
    description:
      'Perched on the highest point overlooking Bhawan. Pilgrimage is spiritually incomplete without Bhairon Nath darshan.',
    significance: 'Divine boon granted by Mata Rani to Bhairon Nath upon his salvation.',
    timings: '24 hours open. Ropeway operates from 08:00 AM to 05:00 PM.',
    darshanTips: 'Passenger ropeway connects Bhawan to Bhairon in 3 minutes (INR 100).',
  },
  {
    id: 'sanjichhat',
    name: 'Sanjichhat Helipad & Viewpoint',
    category: 'High Altitude Plateau',
    altitude: '1,768 m (5,800 ft)',
    description:
      'Scenic plateau featuring the shrine board helipad, emergency hospital, and panoramic views of the Trikuta mountains.',
    significance: 'Primary aerial transit hub; 2.5 km downhill trek to Holy Bhawan.',
    timings: 'Helicopter operations daylight only (weather permitting).',
    darshanTips: 'Battery car service operates from Sanjichhat to Bhawan for elderly pilgrims.',
  },
  {
    id: 'banganga',
    name: 'Banganga Holy River',
    category: 'Base Trek Starting Point',
    altitude: '875 m (2,870 ft)',
    description:
      'The holy stream created by Mata Rani shooting an arrow (Baan) into the earth to quench Veer Langur’s thirst.',
    significance: 'Devotees take holy bath before commencing the uphill trek.',
    timings: 'Open 24 hours. Entry checkpoint for RFID Yatra Parchi.',
    darshanTips: 'Pony and Palki registration stands located just beyond Banganga gate.',
  },
  {
    id: 'charanpaduka',
    name: 'Charan Paduka Temple',
    category: 'Midway Sacred Halt',
    altitude: '1,030 m (3,380 ft)',
    description:
      'The sacred slab bearing the imprints of the divine Mother’s holy feet as she looked back towards Trikuta hill.',
    significance: 'Darshan of holy footprints; 1.5 km uphill from Banganga.',
    timings: 'Open 24 hours with continuous Bhajan kirtan.',
    darshanTips: 'Shrine Board tea/water kiosk available right outside.',
  },
];

const CATEGORIES = ['All', 'Sacred Sanctum', 'Mid Trek Milestone', 'Completing Darshan', 'High Altitude Plateau', 'Base Trek Starting Point'];

export default function TourismScreen({ navigation }) {
  const [spots, setSpots] = useState(CURATED_DESTINATIONS);
  const [filterCat, setFilterCat] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadSpots();
  }, []);

  const loadSpots = async () => {
    setLoading(true);
    try {
      const data = await fetchTourismSpots();
      if (Array.isArray(data) && data.length > 0) {
        setSpots(data);
      }
    } catch (e) {
      // Keep curated destinations
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadSpots();
  };

  const filteredSpots = spots.filter((item) => {
    const matchesCat = filterCat === 'All' || item.category === filterCat;
    const matchesSearch =
      (item.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.significance || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <View style={styles.container}>
      <Header
        title="Holy Pilgrimage Sites"
        subtitle="Mata Vaishno Devi Circuit"
      />

      <View style={styles.searchSection}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search holy spots, caves, temples..."
          placeholderTextColor={colors.textLight}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.categoryScroll}
        >
          {CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[
                styles.categoryChip,
                filterCat === cat && styles.categoryChipActive,
              ]}
              onPress={() => setFilterCat(cat)}
            >
              <Text
                style={[
                  styles.categoryChipText,
                  filterCat === cat && styles.categoryChipTextActive,
                ]}
              >
                {cat}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Fetching pilgrimage data...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredSpots}
          keyExtractor={(item, idx) => item.id || String(idx)}
          renderItem={({ item }) => (
            <TourismCard
              spot={item}
              place={item}
              onAskAssistant={(q) => navigation.navigate('Assistant', { query: q })}
            />
          )}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              colors={[colors.primary]}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No pilgrimage spots found matching "{searchQuery}"</Text>
            </View>
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
  searchSection: {
    backgroundColor: colors.surface,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    ...spacing.shadowSm,
  },
  searchInput: {
    backgroundColor: colors.surfaceSecondary,
    marginHorizontal: spacing.md,
    borderRadius: spacing.radiusSm,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    fontSize: 14,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.borderLight,
    marginBottom: spacing.xs,
  },
  categoryScroll: {
    paddingHorizontal: spacing.md,
    gap: spacing.xs,
    paddingVertical: 4,
  },
  categoryChip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: spacing.radiusSm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  categoryChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  categoryChipText: {
    fontSize: 11,
    color: colors.text,
    fontWeight: '500',
  },
  categoryChipTextActive: {
    color: colors.surface,
    fontWeight: '700',
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
  emptyContainer: {
    padding: spacing.xl,
    alignItems: 'center',
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
});
