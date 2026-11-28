import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, Linking, Modal } from 'react-native';
import * as Speech from 'expo-speech';
import { colors } from '../theme/colors';
import MarkdownView from './MarkdownView';
import ItineraryPreviewCard from './ItineraryPreviewCard';
import YatraLogo from './YatraLogo';
import { VolumeIcon, SquareIcon, TicketIcon, CloseIcon } from './Icons';
import {
  buildAndroidImageSource,
  getImageRequestHeaders,
  resolveImageUri,
  markImageUriFailed,
  isImageUriFailed,
} from '../utils/destinationImages';

function ChatBubble({ message, onNavigateToBooking, onActionPress, onViewFullItinerary }) {
  const isUser = message.role === 'user';
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activePhoto, setActivePhoto] = useState(null);
  const [failedImages, setFailedImages] = useState({});
  const [fallbackUrlMap, setFallbackUrlMap] = useState({});

  useEffect(() => {
    return () => {
      if (isSpeaking) {
        try {
          Speech.stop();
        } catch {
          // ignore
        }
      }
    };
  }, [isSpeaking]);

  const handleBookingHandoff = onNavigateToBooking || onActionPress;

  const toggleSpeech = async () => {
    if (isSpeaking) {
      try {
        Speech.stop();
      } catch {
        // ignore
      }
      setIsSpeaking(false);
      return;
    }

    if (!message.content) return;
    try {
      const cleanText = message.content.replace(/<[^>]+>/g, '').replace(/[*#_`]/g, '');
      // Cap long text to prevent native Android TextToSpeech audio buffer crashes on multi-thousand character itineraries
      const safeTtsText =
        cleanText.length > 800
          ? cleanText.slice(0, 800) + '... To view the complete pilgrimage itinerary, please review the cards below.'
          : cleanText;
      setIsSpeaking(true);
      Speech.speak(safeTtsText, {
        language: 'en-IN',
        rate: 0.95,
        onDone: () => setIsSpeaking(false),
        onError: () => setIsSpeaking(false),
        onStopped: () => setIsSpeaking(false),
      });
    } catch {
      setIsSpeaking(false);
    }
  };

  const hasBookingHandoff =
    !isUser &&
    (message.booking_handoff ||
      message.bookingHandoff ||
      message.action === 'NAVIGATE_TO_BOOKING' ||
      message.status === 'NAVIGATE_TO_BOOKING');

  return (
    <View style={[styles.bubbleContainer, isUser ? styles.userContainer : styles.assistantContainer]}>
      {!isUser && (
        <View style={styles.avatar}>
          <YatraLogo size={24} />
        </View>
      )}

      <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        {!isUser && (
          <View style={styles.assistantHeader}>
            <Text style={styles.assistantLabel}>Yatra AI</Text>
            <TouchableOpacity onPress={toggleSpeech} style={styles.ttsButton} activeOpacity={0.7}>
              {isSpeaking ? (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <SquareIcon size={12} color={colors.royalPlum} />
                  <Text style={styles.ttsText}>Stop</Text>
                </View>
              ) : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <VolumeIcon size={13} color={colors.royalPlum} />
                  <Text style={styles.ttsText}>Listen</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>
        )}

        <MarkdownView
          content={message.content}
          textColor={colors.textPrimary}
        />

        {/* Minimal Itinerary Preview Card when AI response contains a pilgrimage plan */}
        {!isUser && (message.recommendation || message.itinerary || message.plan) && (
          <ItineraryPreviewCard
            recommendation={message.recommendation}
            itinerary={message.itinerary}
            plan={message.plan}
            request={message.request}
            onViewFullItinerary={onViewFullItinerary}
            onProceedBooking={(payload) => {
              if (handleBookingHandoff) {
                handleBookingHandoff(payload);
              }
            }}
          />
        )}

        {/* Verified Destination Photographs Gallery */}
        {(() => {
          if (isUser || !Array.isArray(message.destination_images) || message.destination_images.length === 0) {
            return null;
          }
          const visibleItems = message.destination_images
            .map((item, idx) => {
              const primaryRaw = item.thumbnail_url || item.image_url;
              const useSecondary = Boolean(fallbackUrlMap[idx]);
              const chosenRaw = useSecondary ? (item.image_url || item.thumbnail_url) : primaryRaw;
              const resolvedUri = resolveImageUri(chosenRaw);
              if (failedImages[idx] || !resolvedUri || isImageUriFailed(resolvedUri)) {
                return null;
              }
              const headers = getImageRequestHeaders(resolvedUri);
              const source = headers ? { uri: resolvedUri, headers } : { uri: resolvedUri };
              return { item, idx, resolvedUri, source };
            })
            .filter(Boolean);

          if (visibleItems.length === 0) {
            return null;
          }

          return (
            <View style={styles.galleryContainer}>
              <View style={styles.galleryHeader}>
                <Text style={styles.galleryTitle}>
                  📷 Verified Photos: {message.matched_destination?.name || 'Sightseeing'}
                </Text>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.galleryScroll}>
                {visibleItems.map(({ item, idx, resolvedUri, source }) => (
                  <TouchableOpacity
                    key={idx}
                    style={styles.galleryCard}
                    onPress={() => setActivePhoto({ ...item, resolved_uri: resolvedUri })}
                    activeOpacity={0.85}
                    accessibilityLabel={`View full photo: ${item.title || 'Destination'}`}
                  >
                    <Image
                      source={source || { uri: item.thumbnail_url || item.image_url }}
                      style={styles.galleryImage}
                      resizeMode="cover"
                      onError={() => {
                        markImageUriFailed(resolvedUri);
                        const altUri = resolveImageUri(item.image_url);
                        if (!fallbackUrlMap[idx] && altUri && altUri !== resolvedUri && !isImageUriFailed(altUri)) {
                          setFallbackUrlMap((prev) => ({ ...prev, [idx]: true }));
                        } else {
                          setFailedImages((prev) => ({ ...prev, [idx]: true }));
                        }
                      }}
                    />
                    <View style={styles.galleryCaption}>
                      <Text style={styles.photoTitle} numberOfLines={1}>
                        {item.title || 'Destination Photograph'}
                      </Text>
                      <Text style={styles.photoAttribution} numberOfLines={1}>
                        {item.photographer ? `By ${item.photographer}` : 'Wikimedia Commons'} · {item.license || 'CC'}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          );
        })()}

        {/* Lightbox Image Magnification Modal */}
        {activePhoto && (
          <Modal
            visible={Boolean(activePhoto)}
            transparent
            animationType="fade"
            onRequestClose={() => setActivePhoto(null)}
          >
            <View style={styles.lightboxBackdrop}>
              <View style={styles.lightboxCard}>
                <View style={styles.lightboxTopBar}>
                  <Text style={styles.lightboxTitle} numberOfLines={1}>
                    {activePhoto.title || 'Destination Photograph'}
                  </Text>
                  <TouchableOpacity
                    style={styles.lightboxCloseBtn}
                    onPress={() => setActivePhoto(null)}
                    activeOpacity={0.7}
                  >
                    <CloseIcon size={18} color="#FFFFFF" strokeWidth={2.2} />
                  </TouchableOpacity>
                </View>

                <Image
                  source={
                    buildAndroidImageSource(activePhoto.resolved_uri || activePhoto.thumbnail_url || activePhoto.image_url) ||
                    { uri: activePhoto.thumbnail_url || activePhoto.image_url }
                  }
                  style={styles.lightboxFullImage}
                  resizeMode="contain"
                  onError={() => setActivePhoto(null)}
                />

                <View style={styles.lightboxMetaRow}>
                  <Text style={styles.lightboxAttribution}>
                    {activePhoto.photographer ? `Photo by ${activePhoto.photographer}` : 'Wikimedia Commons'}
                  </Text>
                  {activePhoto.license && (
                    <TouchableOpacity
                      onPress={() => {
                        const url = activePhoto.license_url || activePhoto.source_page_url;
                        if (url) Linking.openURL(url).catch(() => {});
                      }}
                      activeOpacity={0.7}
                    >
                      <Text style={styles.lightboxLicenseLink}>{activePhoto.license} ↗</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            </View>
          </Modal>
        )}

        {/* Booking Handoff Card CTA if action indicates booking */}
        {hasBookingHandoff && handleBookingHandoff && (
          <TouchableOpacity
            style={styles.handoffCard}
            onPress={() => handleBookingHandoff(message.booking_handoff || message.bookingHandoff || message.pending_options || message)}
          >
            <View style={styles.handoffRow}>
              <View style={styles.handoffIconWrapper}>
                <TicketIcon size={18} color={colors.primary} />
              </View>
              <View style={styles.handoffInfo}>
                <Text style={styles.handoffTitle}>
                  {message.bookingHandoff?.title || 'Proceed to Guided Booking Wizard'}
                </Text>
                <Text style={styles.handoffSub}>
                  {message.bookingHandoff?.service
                    ? `Reserve ${message.bookingHandoff.service}`
                    : 'Customize darshan slot, transport & hotel'}
                </Text>
              </View>
            </View>
            <Text style={styles.handoffArrow}>→</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bubbleContainer: {
    flexDirection: 'row',
    marginVertical: 4,
    paddingHorizontal: 8,
  },
  userContainer: {
    justifyContent: 'flex-end',
  },
  assistantContainer: {
    justifyContent: 'flex-start',
  },
  avatar: {
    marginRight: 8,
    marginTop: 2,
  },
  bubble: {
    maxWidth: '85%',
    borderRadius: 18,
    paddingVertical: 9,
    paddingHorizontal: 13,
  },
  userBubble: {
    backgroundColor: colors.softPlum,
    borderBottomRightRadius: 4,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  assistantBubble: {
    maxWidth: '92%',
    backgroundColor: 'transparent',
    borderWidth: 0,
    paddingHorizontal: 2,
    paddingVertical: 2,
    shadowOpacity: 0,
    elevation: 0,
  },
  assistantHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
    paddingBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  assistantLabel: {
    fontSize: 11.5,
    fontWeight: '800',
    color: colors.royalPlum,
    letterSpacing: 0.3,
  },
  ttsButton: {
    paddingVertical: 3,
    paddingHorizontal: 8,
    backgroundColor: colors.surfaceWhite,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  ttsText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.royalPlum,
  },
  handoffCard: {
    marginTop: 10,
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1.2,
    borderColor: colors.borderDefault,
    borderRadius: 12,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    elevation: 1,
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
  },
  handoffRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  handoffIconWrapper: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.softPlum,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  handoffInfo: {
    flex: 1,
  },
  handoffTitle: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.royalPlum,
  },
  handoffSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  handoffArrow: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.royalPlum,
    marginLeft: 6,
  },
  galleryContainer: {
    marginTop: 10,
    backgroundColor: colors.surfaceWhite,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    padding: 10,
    overflow: 'hidden',
  },
  galleryHeader: {
    marginBottom: 8,
  },
  galleryTitle: {
    fontSize: 11.5,
    fontWeight: '700',
    color: colors.royalPlum,
  },
  galleryScroll: {
    flexDirection: 'row',
  },
  galleryCard: {
    width: 175,
    marginRight: 10,
    backgroundColor: colors.surfaceWhite,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    overflow: 'hidden',
  },
  galleryImage: {
    width: '100%',
    height: 110,
    backgroundColor: colors.surfaceSecondary,
  },
  galleryCaption: {
    padding: 7,
  },
  photoTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.royalPlum,
  },
  photoAttribution: {
    fontSize: 9.5,
    color: colors.textSecondary,
    marginTop: 2,
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
    borderColor: colors.champagneTaupe,
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
    color: colors.softChampagne,
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  lightboxAttribution: {
    color: colors.warmBeige,
    fontSize: 11,
    flex: 1,
    marginRight: 8,
  },
  lightboxLicenseLink: {
    color: colors.softChampagne,
    fontSize: 11,
    fontWeight: '700',
    textDecorationLine: 'underline',
  },
});

export default React.memo(ChatBubble);
