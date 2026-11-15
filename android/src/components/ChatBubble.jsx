import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import * as Speech from 'expo-speech';
import { colors } from '../theme/colors';
import MarkdownView from './MarkdownView';
import YatraLogo from './YatraLogo';
import { VolumeIcon, SquareIcon, TicketIcon } from './Icons';

export default function ChatBubble({ message, onNavigateToBooking, onActionPress }) {
  const isUser = message.role === 'user';
  const [isSpeaking, setIsSpeaking] = useState(false);

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
      Speech.stop();
      setIsSpeaking(false);
      return;
    }

    if (!message.content) return;
    const cleanText = message.content.replace(/<[^>]+>/g, '').replace(/[*#_`]/g, '');
    setIsSpeaking(true);
    Speech.speak(cleanText, {
      language: 'en-IN',
      rate: 0.95,
      onDone: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
      onStopped: () => setIsSpeaking(false),
    });
  };

  const hasBookingHandoff =
    !isUser &&
    (message.bookingHandoff ||
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
            <Text style={styles.assistantLabel}>Yatra AI Companion</Text>
            <TouchableOpacity onPress={toggleSpeech} style={styles.ttsButton} activeOpacity={0.7}>
              {isSpeaking ? (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <SquareIcon size={12} color={colors.primary} />
                  <Text style={styles.ttsText}>Stop</Text>
                </View>
              ) : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <VolumeIcon size={13} color={colors.primary} />
                  <Text style={styles.ttsText}>Listen</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>
        )}

        <MarkdownView
          content={message.content}
          textColor={isUser ? colors.textWhite : colors.textPrimary}
        />

        {/* Booking Handoff Card CTA if action indicates booking */}
        {hasBookingHandoff && handleBookingHandoff && (
          <TouchableOpacity
            style={styles.handoffCard}
            onPress={() => handleBookingHandoff(message.bookingHandoff || message.pending_options || null)}
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
    marginVertical: 6,
    paddingHorizontal: 12,
  },
  userContainer: {
    justifyContent: 'flex-end',
  },
  assistantContainer: {
    justifyContent: 'flex-start',
  },
  avatar: {
    marginRight: 8,
    marginTop: 4,
  },
  bubble: {
    maxWidth: '84%',
    borderRadius: 16,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  userBubble: {
    backgroundColor: colors.burgundy,
    borderBottomRightRadius: 2,
  },
  assistantBubble: {
    maxWidth: '88%',
    backgroundColor: colors.bgCard,
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
    borderBottomLeftRadius: 2,
    shadowColor: '#58111A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  assistantHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    paddingBottom: 4,
  },
  assistantLabel: {
    fontSize: 11,
    fontWeight: '800',
    color: colors.burgundy,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  ttsButton: {
    paddingVertical: 2,
    paddingHorizontal: 6,
    backgroundColor: colors.goldSubtle,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  ttsText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.burgundy,
  },
  handoffCard: {
    marginTop: 8,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1.5,
    borderColor: colors.gold,
    borderRadius: 10,
    padding: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  handoffRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  handoffIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  handoffInfo: {
    flex: 1,
  },
  handoffTitle: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.burgundy,
  },
  handoffSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 1,
  },
  handoffArrow: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.burgundy,
    marginLeft: 6,
  },
});
