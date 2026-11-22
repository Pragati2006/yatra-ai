import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { colors } from '../theme/colors';
import { MountainIcon } from './Icons';

export default function TourismCard({ place, spot, onAskAssistant }) {
  const [expanded, setExpanded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const target = place || spot || {};

  const name = target.name || 'Holy Pilgrimage Site';
  const categoryType = target.category_type || null;
  const isReligious = categoryType === 'religious_site' || (!categoryType && !['Nature', 'Hill station', 'Hill station / adventure', 'Kashmir', 'nature_destination', 'historical_site', 'tourist_attraction'].includes(target.category));
  const category = target.category || (isReligious ? 'Holy Shrine' : 'Tourist Attraction');
  const altitude = target.altitude_m ? `~${target.altitude_m} m` : (target.altitude || target.elevation || 'Katra Region');
  const description = target.description || '';
  const distance = target.distance || null;

  const gallery = target.image_gallery || [];
  const imageUrl = target.image_url || (target.image && target.image.startsWith('http') ? target.image : null) || gallery[0]?.thumbnail_url || gallery[0]?.image_url || null;
  const photoMeta = gallery[0] || null;
  const timings = isReligious
    ? (target.darshan_timings || target.timings || null)
    : (target.visiting_hours || (target.visiting_hours_verified ? target.timings : 'Daytime access (weather permitting)'));
  const timingsLabel = isReligious ? 'Darshan Timings:' : 'Visiting Hours:';
  const significance = isReligious ? (target.religious_information || target.significance || null) : (target.historical_background || target.significance || null);
  const significanceLabel = isReligious ? 'Sacred Significance:' : 'Historical / Cultural Background:';
  const bestTime = !isReligious ? target.best_time_to_visit : null;
  const entryFee = target.entry_fee || null;
  const accessibility = !isReligious ? target.accessibility : null;
  const seasonalRestrictions = !isReligious ? target.seasonal_restrictions : null;
  const tips = target.travel_tips || target.darshanTips || null;

  return (
    <View style={styles.card}>
      {imageUrl && !imageError ? (
        <View style={styles.imageContainer}>
          <Image
            source={{ uri: imageUrl }}
            style={styles.cardImage}
            onError={() => setImageError(true)}
            resizeMode="cover"
          />
          {gallery.length > 1 && (
            <View style={styles.photoCountBadge}>
              <Text style={styles.photoCountText}>📷 {gallery.length} photos</Text>
            </View>
          )}
        </View>
      ) : (
        <View style={styles.fallbackNoticeBox}>
          <MountainIcon size={18} color={colors.goldDark} />
          <Text style={styles.fallbackNoticeText}>
            {target.image_notice || 'Verified photograph in archival curation'}
          </Text>
        </View>
      )}

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
              <Text style={styles.detailLabel}>{timingsLabel}</Text>
              <Text style={styles.detailValue}>{timings}</Text>
            </View>
          )}
          {bestTime && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Best Time to Visit:</Text>
              <Text style={styles.detailValue}>{bestTime}</Text>
            </View>
          )}
          {entryFee && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Entry Fee:</Text>
              <Text style={styles.detailValue}>{entryFee}</Text>
            </View>
          )}
          {accessibility && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Accessibility:</Text>
              <Text style={styles.detailValue}>{accessibility}</Text>
            </View>
          )}
          {seasonalRestrictions && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Seasonal Restrictions:</Text>
              <Text style={styles.detailValue}>{seasonalRestrictions}</Text>
            </View>
          )}
          {significance && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>{significanceLabel}</Text>
              <Text style={styles.detailValue}>{significance}</Text>
            </View>
          )}
          {tips && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>{isReligious ? 'Pilgrim Advisory:' : 'Traveler Advisory:'}</Text>
              <Text style={styles.detailValue}>{tips}</Text>
            </View>
          )}
          {photoMeta?.attribution && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Photograph:</Text>
              <Text style={styles.detailValue}>{photoMeta.attribution}</Text>
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
  imageContainer: {
    position: 'relative',
    height: 140,
    borderRadius: 10,
    overflow: 'hidden',
    marginBottom: 10,
    backgroundColor: '#3D0810',
  },
  cardImage: {
    width: '100%',
    height: '100%',
  },
  photoCountBadge: {
    position: 'absolute',
    bottom: 6,
    right: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  photoCountText: {
    color: '#F4E5BE',
    fontSize: 10.5,
    fontWeight: '700',
  },
  fallbackNoticeBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginBottom: 10,
  },
  fallbackNoticeText: {
    flex: 1,
    fontSize: 11,
    color: colors.textSecondary,
    fontStyle: 'italic',
  },
});
