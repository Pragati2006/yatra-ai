import React, { useState, useEffect, useMemo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, ActivityIndicator, Modal } from 'react-native';
import { colors } from '../theme/colors';
import { CloseIcon } from './Icons';
import {
  VERIFIED_DESTINATION_GALLERIES,
  getCandidateImageUrls,
  buildAndroidImageSource,
  markImageUriFailed,
} from '../utils/destinationImages';

export default function TourismCard({ place, spot, onAskAssistant }) {
  const [expanded, setExpanded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [candidateIdx, setCandidateIdx] = useState(0);
  const target = place || spot || {};

  const name = target.name || 'Holy Pilgrimage Site';
  const categoryType = target.category_type || null;
  const isReligious = categoryType === 'religious_site' || (!categoryType && !['Nature', 'Hill station', 'Hill station / adventure', 'Kashmir', 'nature_destination', 'historical_site', 'tourist_attraction'].includes(target.category));
  const category = target.category || (isReligious ? 'Holy Shrine' : 'Tourist Attraction');
  const altitude = target.altitude_m ? `~${target.altitude_m} m` : (target.altitude || target.elevation || 'Katra Region');
  const description = target.description || '';
  const distance = target.distance || null;

  // Resolve gallery from target or local verified catalogue
  const localEntry =
    VERIFIED_DESTINATION_GALLERIES[name] ||
    VERIFIED_DESTINATION_GALLERIES[target.name] ||
    Object.values(VERIFIED_DESTINATION_GALLERIES).find(
      (v) => (v.name || '').toLowerCase() === (name || '').toLowerCase()
    ) ||
    null;

  const gallery =
    Array.isArray(target.image_gallery) && target.image_gallery.length > 0
      ? target.image_gallery
      : localEntry?.images || [];

  const candidateUrls = useMemo(
    () => getCandidateImageUrls(target, gallery),
    [name, target.image_url, target.thumbnail_url, target.image, gallery]
  );

  useEffect(() => {
    setCandidateIdx(0);
    setImageError(candidateUrls.length === 0);
  }, [name, candidateUrls.length]);

  const rawCandidate = candidateUrls[candidateIdx] || null;
  let imageUrl = null;
  if (rawCandidate) {
    try {
      imageUrl = encodeURI(decodeURI(rawCandidate));
    } catch {
      imageUrl = rawCandidate;
    }
  }
  const imageSourceMeta = imageUrl ? buildAndroidImageSource(imageUrl) : null;

  const photoMeta = gallery[0] || (imageUrl ? { title: name, image_url: imageUrl, thumbnail_url: imageUrl } : null);
  const lightboxUrl = imageUrl || photoMeta?.thumbnail_url || photoMeta?.image_url || null;
  const lightboxSource = lightboxUrl ? buildAndroidImageSource(lightboxUrl) : null;
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
        <TouchableOpacity
          style={styles.imageContainer}
          onPress={() => setLightboxOpen(true)}
          activeOpacity={0.9}
          accessibilityLabel={`View full photo for ${name}`}
        >
          <Image
            source={imageSourceMeta?.headers ? { uri: imageUrl, headers: imageSourceMeta.headers } : { uri: imageUrl }}
            style={styles.cardImage}
            onLoadStart={() => setImageLoading(true)}
            onLoadEnd={() => setImageLoading(false)}
            onError={() => {
              setImageLoading(false);
              if (imageUrl) markImageUriFailed(imageUrl);
              if (candidateIdx < candidateUrls.length - 1) {
                setCandidateIdx((prev) => prev + 1);
              } else {
                setImageError(true);
              }
            }}
            resizeMode="cover"
          />
          {imageLoading && (
            <View style={styles.imageLoadingOverlay}>
              <ActivityIndicator size="small" color={colors.goldDark} />
            </View>
          )}
          {gallery.length > 1 && (
            <View style={styles.photoCountBadge}>
              <Text style={styles.photoCountText}>📷 {gallery.length} photos</Text>
            </View>
          )}
        </TouchableOpacity>
      ) : null}

      {/* Lightbox Modal */}
      {lightboxOpen && photoMeta && !imageError && lightboxUrl && (
        <Modal
          visible={lightboxOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setLightboxOpen(false)}
        >
          <View style={styles.lightboxBackdrop}>
            <View style={styles.lightboxCard}>
              <View style={styles.lightboxTopBar}>
                <Text style={styles.lightboxTitle} numberOfLines={1}>
                  {name} — {photoMeta.title || 'Verified Photograph'}
                </Text>
                <TouchableOpacity
                  style={styles.lightboxCloseBtn}
                  onPress={() => setLightboxOpen(false)}
                  activeOpacity={0.7}
                >
                  <CloseIcon size={18} color="#FFFFFF" strokeWidth={2.2} />
                </TouchableOpacity>
              </View>

              <Image
                source={lightboxSource || { uri: lightboxUrl }}
                style={styles.lightboxFullImage}
                resizeMode="contain"
                onError={() => setLightboxOpen(false)}
              />

              <View style={styles.lightboxMetaRow}>
                <Text style={styles.lightboxAttribution} numberOfLines={2}>
                  {photoMeta.attribution || (photoMeta.photographer ? `Photo by ${photoMeta.photographer}` : 'Wikimedia Commons')}
                </Text>
              </View>
            </View>
          </View>
        </Modal>
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
  imageLoadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(61, 8, 16, 0.4)',
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
  lightboxBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(26, 12, 18, 0.92)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  lightboxCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#240B15',
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
  },
  lightboxTopBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(163, 130, 108, 0.3)',
  },
  lightboxTitle: {
    color: '#F4E5BE',
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
    marginRight: 8,
  },
  lightboxCloseBtn: {
    padding: 4,
  },
  lightboxFullImage: {
    width: '100%',
    height: 260,
    backgroundColor: '#15050C',
  },
  lightboxMetaRow: {
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  lightboxAttribution: {
    color: '#E0D0C0',
    fontSize: 11,
  },
});
