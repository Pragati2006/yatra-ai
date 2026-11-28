import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { colors } from '../theme/colors';
import {
  MountainIcon,
  UserIcon,
  CalendarIcon,
  TicketIcon,
  ArrowRightIcon,
  ClockIcon,
  CheckIcon,
} from './Icons';
import { upsertItinerary } from '../services/api';

/**
 * android/src/components/ItineraryPreviewCard.jsx
 *
 * Minimal Itinerary Preview Card displayed directly in the Assistant chat stream.
 *
 * Requirements:
 * 1. Destination & trip duration
 * 2. Number of travellers
 * 3. Origin & travel dates (when available)
 * 4. Concise day-wise overview
 * 5. Estimated total budget
 * 6. Primary Action: Prominent "View Full Itinerary" button
 * 7. Secondary Action: Direct "Proceed with Booking" button
 */
function ItineraryPreviewCard({
  recommendation,
  itinerary,
  plan,
  request,
  onViewFullItinerary,
  onProceedBooking,
}) {
  const [savedFlag, setSavedFlag] = useState(false);
  const prof = recommendation?.profile || {};
  const destination =
    recommendation?.destination ||
    prof.destination ||
    request?.destination ||
    'Shri Mata Vaishno Devi Shrine';
  const pax = prof.pax || request?.pax || 2;
  const groupType = prof.group_type || request?.group_type || 'Family';
  const duration = prof.duration_days || request?.duration_days || 4;
  const nights = Math.max(1, duration - 1);
  const origin = prof.origin || request?.origin || null;
  const startDate = prof.start_date || request?.start_date || null;
  const endDate = prof.end_date || request?.end_date || null;

  const rawGrandTotal =
    plan?.budget_evaluation?.grand_total ||
    recommendation?.estimated_total_budget ||
    null;
  const grandTotal = typeof rawGrandTotal === 'number' && !isNaN(rawGrandTotal) ? rawGrandTotal : null;
  const estTotalStr = grandTotal
    ? `₹${Math.round(grandTotal).toLocaleString('en-IN')}`
    : '₹14,500';

  // Extract day-wise overview highlights
  const rawItin = itinerary || recommendation?.itinerary || plan?.itinerary || null;
  const itinDays = rawItin?.days || (Array.isArray(rawItin) ? rawItin : []);

  const dayHighlights = [];
  if (itinDays && itinDays.length > 0) {
    itinDays.forEach((d, idx) => {
      if (!d) return;
      const dayNum = d.day_number || d.day || idx + 1;
      const title =
        d.title ||
        d.theme ||
        (Array.isArray(d.activities) && d.activities[0]?.activity
          ? d.activities[0].activity
          : Array.isArray(d.activities) && typeof d.activities[0] === 'string'
          ? d.activities[0]
          : `Day ${dayNum} Yatra Program`);
      dayHighlights.push({
        dayNum,
        title: typeof title === 'string' ? title : `Day ${dayNum} Yatra Activities`,
      });
    });
  } else {
    const defaultThemes = [
      'Arrival at Katra, Hotel Check-in & RFID Registration',
      'Sacred Trek to Bhawan, Mata Vaishno Devi Darshan & Aarti',
      'Bhairavnath Temple & Scenic Patnitop / Shiv Khori Excursion',
      'Morning Souvenir Shopping & Departure with Holy Blessings',
    ];
    for (let i = 0; i < duration; i++) {
      dayHighlights.push({
        dayNum: i + 1,
        title: defaultThemes[i] || `Day ${i + 1} Regional Pilgrimage & Sacred Excursion`,
      });
    }
  }

  const payload = {
    destination,
    duration,
    pax,
    groupType,
    origin,
    startDate,
    endDate,
    grandTotal,
    itinerary: rawItin,
    recommendation,
    plan,
    request,
    dayHighlights,
  };

  return (
    <View style={styles.cardContainer}>
      {/* 1. Header with Golden Pilgrimage Badge */}
      <View style={styles.badgeRow}>
        <View style={styles.headerBadge}>
          <Text style={styles.headerBadgeText}>PERSONALIZED PILGRIMAGE PLAN</Text>
        </View>
        <Text style={styles.durationPill}>
          {duration} Days / {nights} {nights === 1 ? 'Night' : 'Nights'}
        </Text>
      </View>

      {/* Destination Title */}
      <Text style={styles.destinationTitle}>{destination}</Text>

      {/* 2. Key Metadata Badges */}
      <View style={styles.metaRow}>
        <View style={styles.metaChip}>
          <UserIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
          <Text style={styles.metaChipText}>
            {pax} {pax === 1 ? 'Devotee' : 'Devotees'} ({groupType})
          </Text>
        </View>

        {origin && (
          <View style={styles.metaChip}>
            <MountainIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
            <Text style={styles.metaChipText}>From {origin}</Text>
          </View>
        )}

        {startDate && (
          <View style={styles.metaChip}>
            <CalendarIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
            <Text style={styles.metaChipText}>{startDate}</Text>
          </View>
        )}
      </View>

      {/* 3. Concise Day-Wise Highlights */}
      <View style={styles.timelineBox}>
        <Text style={styles.timelineHeading}>📅 DAY-WISE OVERVIEW</Text>
        {dayHighlights.length <= 7 ? (
          dayHighlights.map((day) => (
            <View key={day.dayNum} style={styles.timelineRow}>
              <View style={styles.dayDotContainer}>
                <View style={styles.dayDot} />
                <Text style={styles.dayLabel}>D{day.dayNum}</Text>
              </View>
              <Text style={styles.dayText} numberOfLines={2}>
                {day.title}
              </Text>
            </View>
          ))
        ) : (
          <>
            {dayHighlights.slice(0, 4).map((day) => (
              <View key={day.dayNum} style={styles.timelineRow}>
                <View style={styles.dayDotContainer}>
                  <View style={styles.dayDot} />
                  <Text style={styles.dayLabel}>D{day.dayNum}</Text>
                </View>
                <Text style={styles.dayText} numberOfLines={2}>
                  {day.title}
                </Text>
              </View>
            ))}
            <View style={styles.timelineRow}>
              <View style={styles.dayDotContainer}>
                <View style={styles.dayDot} />
                <Text style={styles.dayLabel}>D5–{dayHighlights[dayHighlights.length - 1].dayNum - 1}</Text>
              </View>
              <Text style={styles.dayText} numberOfLines={2}>
                Regional Pilgrimage & Sacred Excursions ({dayHighlights.length - 5} intermediate days)
              </Text>
            </View>
            <View key={dayHighlights[dayHighlights.length - 1].dayNum} style={styles.timelineRow}>
              <View style={styles.dayDotContainer}>
                <View style={styles.dayDot} />
                <Text style={styles.dayLabel}>D{dayHighlights[dayHighlights.length - 1].dayNum}</Text>
              </View>
              <Text style={styles.dayText} numberOfLines={2}>
                {dayHighlights[dayHighlights.length - 1].title}
              </Text>
            </View>
          </>
        )}
      </View>

      {/* 4. Estimated Budget Banner */}
      <View style={styles.budgetRow}>
        <View>
          <Text style={styles.budgetLabel}>ESTIMATED TOTAL BUDGET</Text>
          <Text style={styles.budgetAmount}>{estTotalStr}</Text>
        </View>
        <Text style={styles.budgetSub}>For {pax} pilgrims incl. stay & travel</Text>
      </View>

      {/* 5. Actions: Primary (View Full Itinerary) & Secondary (Proceed with Booking) */}
      <View style={styles.actionsContainer}>
        <TouchableOpacity
          style={styles.primaryBtn}
          onPress={() => onViewFullItinerary && onViewFullItinerary(payload)}
          activeOpacity={0.85}
          accessibilityLabel="View Full Itinerary"
        >
          <Text style={styles.primaryBtnText}>View Full Itinerary</Text>
          <ArrowRightIcon size={16} color="#FFFFFF" strokeWidth={2.5} />
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryBtn}
          onPress={() => onProceedBooking && onProceedBooking(payload)}
          activeOpacity={0.8}
          accessibilityLabel="Proceed with Booking"
        >
          <TicketIcon size={15} color={colors.royalPlum} strokeWidth={2.2} />
          <Text style={styles.secondaryBtnText}>Proceed with Booking</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.secondaryBtn, savedFlag && { backgroundColor: '#D1FAE5', borderColor: '#34D399' }]}
          onPress={async () => {
            try {
              const title = `${destination} (${duration} Days)`;
              const daysPayload =
                Array.isArray(itinDays) && itinDays.length > 0
                  ? itinDays
                  : dayHighlights.map((dh) => ({ day_number: dh.dayNum, title: dh.title, activities: [dh.title] }));
              await upsertItinerary({
                title,
                sourceKey: `android-card-${destination}-${duration}-${startDate || 'flex'}`,
                itinerary: {
                  title,
                  destination,
                  start_date: startDate || undefined,
                  end_date: endDate || undefined,
                  duration_days: duration,
                  travellers_count: pax,
                  request,
                  days: daysPayload,
                },
              });
              setSavedFlag(true);
            } catch (err) {
              Alert.alert('Sign In Required', 'Please sign in via Email OTP to save this itinerary to your account.');
            }
          }}
          activeOpacity={0.8}
          accessibilityLabel="Save to My Itineraries"
        >
          <CheckIcon size={15} color={savedFlag ? '#065F46' : colors.royalPlum} strokeWidth={2.2} />
          <Text style={[styles.secondaryBtnText, savedFlag && { color: '#065F46' }]}>
            {savedFlag ? 'Saved to Itineraries' : 'Save Itinerary'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: colors.surfaceWhite || '#FFFFFF',
    borderWidth: 1.2,
    borderColor: colors.borderDefault || '#E9DED6',
    borderRadius: 14,
    padding: 14,
    marginVertical: 10,
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  headerBadge: {
    backgroundColor: 'rgba(84, 21, 45, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  headerBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    letterSpacing: 0.5,
  },
  durationPill: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.champagneTaupe || '#A3826C',
  },
  destinationTitle: {
    fontSize: 16.5,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 10,
  },
  metaChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.softPlum || '#F0E3E7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  metaChipText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: colors.royalPlum || '#54152D',
  },
  timelineBox: {
    backgroundColor: '#FAF7F5',
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.borderSubtle || '#F5ECE6',
  },
  timelineHeading: {
    fontSize: 10.5,
    fontWeight: '800',
    color: colors.champagneTaupe || '#A3826C',
    letterSpacing: 0.4,
    marginBottom: 6,
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  dayDotContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: 36,
  },
  dayDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.royalPlum || '#54152D',
    marginRight: 4,
  },
  dayLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
  },
  dayText: {
    fontSize: 12.5,
    color: colors.textPrimary || '#30272A',
    flex: 1,
    lineHeight: 17,
  },
  budgetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.softPlum || '#F0E3E7',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 12,
  },
  budgetLabel: {
    fontSize: 9.5,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    letterSpacing: 0.4,
  },
  budgetAmount: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
  },
  budgetSub: {
    fontSize: 10.5,
    color: colors.textSecondary || '#736B66',
    maxWidth: 130,
    textAlign: 'right',
  },
  actionsContainer: {
    gap: 8,
  },
  primaryBtn: {
    backgroundColor: colors.royalPlum || '#54152D',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  primaryBtnText: {
    color: '#FFFFFF',
    fontSize: 13.5,
    fontWeight: '700',
  },
  secondaryBtn: {
    backgroundColor: 'transparent',
    borderWidth: 1.2,
    borderColor: colors.borderDefault || '#E9DED6',
    borderRadius: 10,
    paddingVertical: 9,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  secondaryBtnText: {
    color: colors.royalPlum || '#54152D',
    fontSize: 12.5,
    fontWeight: '700',
  },
});

export default React.memo(ItineraryPreviewCard);