import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors } from '../theme/colors';

export default function HotelCard({ hotel, onSelect }) {
  if (!hotel) return null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBox}>
          <Text style={styles.hotelName}>{hotel.name}</Text>
          <Text style={styles.locationSub}>{hotel.location || 'Katra Town'}</Text>
        </View>

        <View style={styles.categoryBadge}>
          <Text style={styles.categoryText}>{hotel.category || hotel.type || 'Shrine Board Bhawan'}</Text>
        </View>
      </View>

      <Text style={styles.desc}>{hotel.description || 'Verified accommodation with basic pilgrim facilities.'}</Text>

      {/* Facilities & Distance */}
      <View style={styles.infoGrid}>
        {hotel.distance && (
          <View style={styles.infoCol}>
            <Text style={styles.infoLabel}>Distance:</Text>
            <Text style={styles.infoVal}>{hotel.distance}</Text>
          </View>
        )}
        {hotel.tariff && (
          <View style={styles.infoCol}>
            <Text style={styles.infoLabel}>Tariff Bracket:</Text>
            <Text style={styles.tariffVal}>{hotel.tariff}</Text>
          </View>
        )}
      </View>

      {/* Select for Booking CTA */}
      {onSelect && (
        <TouchableOpacity
          style={styles.selectBtn}
          onPress={onSelect}
          activeOpacity={0.75}
        >
          <Text style={styles.selectBtnText}>Select for Yatra Booking →</Text>
        </TouchableOpacity>
      )}

      {/* Honest Inventory Notice */}
      <View style={styles.noticeBox}>
        <Text style={styles.noticeText}>
          Real-time room booking requires in-person Shrine Board counter registration (Niharika Complex) or official maavaishnodevi.org portal.
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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  titleBox: {
    flex: 1,
    marginRight: 8,
  },
  hotelName: {
    fontSize: 15.5,
    fontWeight: '800',
    color: colors.burgundy,
  },
  locationSub: {
    fontSize: 11.5,
    color: colors.textSecondary,
    fontWeight: '600',
    marginTop: 2,
  },
  categoryBadge: {
    backgroundColor: colors.goldSubtle,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  categoryText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.burgundy,
  },
  desc: {
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 18,
    marginBottom: 8,
  },
  infoGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.bgSubtle,
    borderRadius: 8,
    padding: 8,
    marginBottom: 8,
  },
  infoCol: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
  },
  infoVal: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.burgundy,
    marginTop: 1,
  },
  tariffVal: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.goldDark,
    marginTop: 1,
  },
  selectBtn: {
    backgroundColor: colors.goldSubtle,
    borderWidth: 1.2,
    borderColor: colors.gold,
    paddingVertical: 7,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 6,
  },
  selectBtnText: {
    color: colors.burgundy,
    fontSize: 12,
    fontWeight: '700',
  },
  noticeBox: {
    paddingTop: 4,
  },
  noticeText: {
    fontSize: 10.5,
    color: colors.textMuted,
    lineHeight: 14,
    fontStyle: 'italic',
  },
});
