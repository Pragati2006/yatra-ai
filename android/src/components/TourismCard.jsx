import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors } from '../theme/colors';

export default function TourismCard({ place, spot, onAskAssistant }) {
  const [expanded, setExpanded] = useState(false);
  const target = place || spot || {};

  const name = target.name || 'Holy Pilgrimage Site';
  const category = target.category || 'Holy Shrine';
  const altitude = target.altitude || target.elevation || 'Katra Region';
  const description = target.description || '';
  const distance = target.distance || null;
  const timings = target.darshan_timings || target.timings || null;
  const significance = target.significance || null;
  const tips = target.travel_tips || target.darshanTips || null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleContainer}>
          <Text style={styles.placeName}>{name}</Text>
          <Text style={styles.categoryBadge}>{category}</Text>
        </View>
        <Text style={styles.altitudeText}>{altitude}</Text>
      </View>

      <Text style={styles.description} numberOfLines={expanded ? undefined : 3}>
        {description}
      </Text>

      {/* Expanded Particulars */}
      {expanded && (
        <View style={styles.detailsBox}>
          {distance && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Distance from Bhawan/Katra:</Text>
              <Text style={styles.detailValue}>{distance}</Text>
            </View>
          )}
          {timings && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Darshan Timings:</Text>
              <Text style={styles.detailValue}>{timings}</Text>
            </View>
          )}
          {significance && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Sacred Significance:</Text>
              <Text style={styles.detailValue}>{significance}</Text>
            </View>
          )}
          {tips && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Pilgrim Advisory:</Text>
              <Text style={styles.detailValue}>{tips}</Text>
            </View>
          )}
        </View>
      )}

      {/* Action Row */}
      <View style={styles.footerRow}>
        <TouchableOpacity onPress={() => setExpanded(!expanded)} style={styles.expandBtn}>
          <Text style={styles.expandText}>{expanded ? 'Show Less ▲' : 'View Guidelines ▼'}</Text>
        </TouchableOpacity>

        {onAskAssistant && (
          <TouchableOpacity
            style={styles.askBtn}
            onPress={() => onAskAssistant(`Tell me details about visiting ${name}`)}
          >
            <Text style={styles.askBtnText}>Ask AI</Text>
          </TouchableOpacity>
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
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  titleContainer: {
    flex: 1,
    marginRight: 8,
  },
  placeName: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.burgundy,
  },
  categoryBadge: {
    fontSize: 11,
    color: colors.goldDark,
    fontWeight: '700',
    marginTop: 2,
  },
  altitudeText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textSecondary,
    backgroundColor: colors.goldSubtle,
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  description: {
    fontSize: 13.5,
    color: colors.textPrimary,
    lineHeight: 19,
    marginBottom: 8,
  },
  detailsBox: {
    backgroundColor: colors.bgSubtle,
    padding: 10,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  detailRow: {
    marginBottom: 6,
  },
  detailLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.burgundy,
  },
  detailValue: {
    fontSize: 12.5,
    color: colors.textSecondary,
    marginTop: 1,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
    paddingTop: 8,
  },
  expandText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.burgundy,
  },
  askBtn: {
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  askBtnText: {
    fontSize: 11.5,
    fontWeight: '700',
    color: colors.burgundy,
  },
});
