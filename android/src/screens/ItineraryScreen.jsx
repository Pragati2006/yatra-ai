import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { colors } from '../theme/colors';
import Header from '../components/Header';
import {
  MountainIcon,
  TrainIcon,
  BuildingIcon,
  CalendarIcon,
  TicketIcon,
  ClockIcon,
  CheckIcon,
  AlertCircleIcon,
  UserIcon,
} from '../components/Icons';
import {
  REALISTIC_TRANSPORTS,
  ASCENT_MODES,
  ACCOMMODATION_CATALOGUE,
} from './BookingScreen';

/**
 * android/src/screens/ItineraryScreen.jsx
 *
 * Dedicated Full Itinerary Screen for Yatra AI Android.
 *
 * Displays:
 * 1. Day-by-day complete schedule with activity highlights and timings
 * 2. Sightseeing recommendations (feasible and infeasible places)
 * 3. Transport recommendations with interactive customization controls
 * 4. Accommodation options with interactive customization controls
 * 5. Detailed budget breakdown (transport, lodging, meals, darshan, total)
 * 6. Direct booking handoff to Guided Booking without re-generating
 * 7. Complete data preservation across back-and-forth navigation
 */
export default function ItineraryScreen({ route, navigation }) {
  const params = route?.params || {};
  const req = params.request || params.recommendation?.profile || {};

  const destination =
    params.destination ||
    req.destination ||
    'Shri Mata Vaishno Devi Shrine';
  const duration = parseInt(params.duration || req.duration_days || 4, 10);
  const nights = Math.max(1, duration - 1);
  const pax = parseInt(params.pax || req.pax || 2, 10);
  const origin = params.origin || req.origin || 'New Delhi';
  const initialStartDate = params.startDate || req.start_date || '2026-11-25';

  // Editable trip states
  const [startDate, setStartDate] = useState(initialStartDate);
  const [selectedTransport, setSelectedTransport] = useState(() => {
    if (params.selected_option?.transport_id) {
      const match = REALISTIC_TRANSPORTS.find((t) => t.id === params.selected_option.transport_id);
      if (match) return match;
    }
    return REALISTIC_TRANSPORTS[0]; // Vande Bharat Express
  });

  const [selectedHotel, setSelectedHotel] = useState(() => {
    if (params.hotel?.hotel_id) {
      const match = ACCOMMODATION_CATALOGUE.find((h) => h.id === params.hotel.hotel_id);
      if (match) return match;
    }
    return ACCOMMODATION_CATALOGUE[2]; // Hotel Asia Katra
  });

  const [selectedAscent, setSelectedAscent] = useState(ASCENT_MODES[0]);
  const [showTransportPicker, setShowTransportPicker] = useState(false);
  const [showHotelPicker, setShowHotelPicker] = useState(false);

  // Day-wise Schedule data
  const rawItin = params.itinerary || params.recommendation?.itinerary || params.plan?.itinerary || null;
  const itinDays = rawItin?.days || (Array.isArray(rawItin) ? rawItin : []);

  // Sightseeing places
  const feasiblePlaces = params.feasible_places || params.recommendation?.suggested_places || [
    'Banganga Holy Checkpoint',
    'Charan Paduka Temple',
    'Ardhkuwari Holy Cave',
    'Mata Vaishno Devi Bhawan',
    'Bhairavnath Temple & Ropeway',
  ];

  const infeasiblePlaces = params.infeasible_places || [];

  // Recalculate itemized budget dynamically based on user selections
  const roomsCount = Math.ceil(pax / 2);
  const transportCost = (selectedTransport?.pricePerPerson || 1665) * pax;
  const ascentCost = (selectedAscent?.pricePerPerson || 0) * pax;
  const hotelCost = (selectedHotel?.pricePerNight || 2400) * roomsCount * nights;
  const mealsCost = 350 * pax * duration;
  const grandTotal = transportCost + ascentCost + hotelCost + mealsCost;
  const perPersonCost = Math.round(grandTotal / pax);

  // Direct Handoff to Booking Screen (Step 2: Review Itinerary / Step 3)
  const handleProceedBooking = () => {
    navigation.navigate('Booking', {
      origin,
      destination,
      startDate,
      duration,
      pax,
      budget: grandTotal,
      selectedTransport,
      selectedHotel,
      selectedAscent,
      step: 2, // Lands on Step 2 with full selections pre-populated
      overrideDraft: true,
      itinerary: rawItin,
    });
  };

  return (
    <View style={styles.screen}>
      <Header
        title="SACRED ITINERARY"
        subtitle={`${destination} · ${duration}D/${nights}N`}
        showBack={true}
        onBackPress={() => {
          if (navigation.canGoBack()) {
            navigation.goBack();
          } else {
            navigation.navigate('Assistant');
          }
        }}
      />

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
      >
        {/* 1. Trip Overview Card */}
        <View style={styles.overviewCard}>
          <View style={styles.overviewBadgeRow}>
            <View style={styles.sacredBadge}>
              <Text style={styles.sacredBadgeText}>VERIFIED PILGRIMAGE ITINERARY</Text>
            </View>
            <Text style={styles.nightsBadge}>{duration} Days / {nights} Nights</Text>
          </View>

          <Text style={styles.destinationHeading}>{destination}</Text>

          <View style={styles.chipsRow}>
            <View style={styles.metaChip}>
              <UserIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.metaChipText}>{pax} Devotees</Text>
            </View>

            <View style={styles.metaChip}>
              <MountainIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.metaChipText}>From {origin}</Text>
            </View>

            <View style={styles.metaChip}>
              <CalendarIcon size={13} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.metaChipText}>Start: {startDate}</Text>
            </View>
          </View>
        </View>

        {/* 2. Day-by-Day Schedule Timeline */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <CalendarIcon size={17} color={colors.royalPlum} strokeWidth={2.2} />
            <Text style={styles.sectionTitle}>Day-by-Day Pilgrimage Schedule</Text>
          </View>

          {itinDays && itinDays.length > 0 ? (
            itinDays.map((d, idx) => {
              const dayNum = d.day_number || d.day || idx + 1;
              const title = d.title || d.theme || `Day ${dayNum} Schedule`;
              const activities = Array.isArray(d.activities) ? d.activities : [];

              return (
                <View key={`day-${dayNum}`} style={styles.dayCard}>
                  <View style={styles.dayHeaderRow}>
                    <View style={styles.dayBadge}>
                      <Text style={styles.dayBadgeText}>DAY {dayNum}</Text>
                    </View>
                    <Text style={styles.dayThemeText} numberOfLines={1}>
                      {title}
                    </Text>
                  </View>

                  {activities.map((act, actIdx) => {
                    const actText = typeof act === 'string' ? act : act.activity || act.description || 'Devotional activity';
                    const timeText = typeof act === 'object' && act.time ? act.time : null;

                    return (
                      <View key={`act-${actIdx}`} style={styles.activityRow}>
                        <View style={styles.activityDot} />
                        <View style={styles.activityBody}>
                          {timeText && <Text style={styles.activityTime}>{timeText}</Text>}
                          <Text style={styles.activityDesc}>{actText}</Text>
                        </View>
                      </View>
                    );
                  })}
                </View>
              );
            })
          ) : (
            // Standard fallback schedule for Vaishno Devi
            [
              {
                day: 1,
                title: 'Arrival at Katra Base Camp & Hotel Check-in',
                desc: 'Arrive at SVDK Railway Station / Katra. Hotel check-in, freshen up, and collect physical Yatra RFID Access Card from Shrine counter.',
              },
              {
                day: 2,
                title: 'Sacred Trek & Mata Vaishno Devi Darshan',
                desc: 'Early morning trek via Banganga, Charan Paduka, and Ardhkuwari. Attend Holy Darshan at Bhawan, followed by Bhairavnath Temple visit.',
              },
              {
                day: 3,
                title: 'Descent to Katra & Regional Excursion',
                desc: 'Descend safely back to Katra base. Relaxing afternoon with optional excursion to Shiv Khori or Patnitop cedar groves.',
              },
              {
                day: 4,
                title: 'Morning Aarti & Return Journey',
                desc: 'Attend morning prayers, purchase prasad & dry fruits in Katra bazaar, and board return train with sacred blessings.',
              },
            ].map((item) => (
              <View key={`fallback-day-${item.day}`} style={styles.dayCard}>
                <View style={styles.dayHeaderRow}>
                  <View style={styles.dayBadge}>
                    <Text style={styles.dayBadgeText}>DAY {item.day}</Text>
                  </View>
                  <Text style={styles.dayThemeText}>{item.title}</Text>
                </View>
                <View style={styles.activityRow}>
                  <View style={styles.activityDot} />
                  <Text style={styles.activityDesc}>{item.desc}</Text>
                </View>
              </View>
            ))
          )}
        </View>

        {/* 3. Sightseeing & Activity Highlights */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <MountainIcon size={17} color={colors.royalPlum} strokeWidth={2.2} />
            <Text style={styles.sectionTitle}>Sightseeing & Holy Sites</Text>
          </View>

          <Text style={styles.subsectionLabel}>Recommended Highlights</Text>
          <View style={styles.sightseeingList}>
            {feasiblePlaces.map((place, idx) => (
              <View key={`feas-${idx}`} style={styles.feasibleRow}>
                <CheckIcon size={15} color={colors.royalPlum} strokeWidth={2.5} />
                <Text style={styles.feasibleText}>
                  {typeof place === 'string' ? place : place.name || 'Holy Site'}
                </Text>
              </View>
            ))}
          </View>

          {infeasiblePlaces.length > 0 && (
            <View style={styles.infeasibleBox}>
              <View style={styles.infeasibleHeader}>
                <AlertCircleIcon size={14} color="#856404" strokeWidth={2.2} />
                <Text style={styles.infeasibleHeading}>Advisory: Time-Constrained Sites</Text>
              </View>
              {infeasiblePlaces.map((item, idx) => (
                <Text key={`inf-${idx}`} style={styles.infeasibleItem}>
                  • {typeof item === 'string' ? item : item.name}: excluded to maintain reasonable darshan pace.
                </Text>
              ))}
            </View>
          )}
        </View>

        {/* 4. Transport Recommendations & Customization */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderBetween}>
            <View style={styles.sectionHeader}>
              <TrainIcon size={17} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.sectionTitle}>Transport Selection</Text>
            </View>
            <TouchableOpacity
              onPress={() => setShowTransportPicker(!showTransportPicker)}
              style={styles.editPill}
              activeOpacity={0.7}
            >
              <Text style={styles.editPillText}>{showTransportPicker ? 'Done' : 'Change'}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.selectedOptionBox}>
            <View style={styles.optionHeader}>
              <Text style={styles.optionName}>{selectedTransport.name}</Text>
              <Text style={styles.optionPrice}>₹{selectedTransport.pricePerPerson} / person</Text>
            </View>
            <Text style={styles.optionRoute}>{selectedTransport.route}</Text>
            <Text style={styles.optionTiming}>
              Dep: {selectedTransport.depTime} · Arr: {selectedTransport.arrTime} ({selectedTransport.duration})
            </Text>
          </View>

          {/* Interactive Transport Options Picker */}
          {showTransportPicker && (
            <View style={styles.pickerContainer}>
              <Text style={styles.pickerTitle}>Available Transport Alternatives:</Text>
              {REALISTIC_TRANSPORTS.map((t) => {
                const isCur = t.id === selectedTransport.id;
                return (
                  <TouchableOpacity
                    key={t.id}
                    style={[styles.pickerItem, isCur && styles.pickerItemActive]}
                    onPress={() => {
                      setSelectedTransport(t);
                      setShowTransportPicker(false);
                    }}
                    activeOpacity={0.8}
                  >
                    <View style={styles.pickerItemInfo}>
                      <Text style={[styles.pickerItemName, isCur && styles.pickerItemNameActive]}>
                        {t.name}
                      </Text>
                      <Text style={styles.pickerItemSub}>{t.route} · {t.duration}</Text>
                    </View>
                    <Text style={styles.pickerItemPrice}>₹{t.pricePerPerson}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
        </View>

        {/* 5. Accommodation Options & Customization */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderBetween}>
            <View style={styles.sectionHeader}>
              <BuildingIcon size={17} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.sectionTitle}>Accommodation</Text>
            </View>
            <TouchableOpacity
              onPress={() => setShowHotelPicker(!showHotelPicker)}
              style={styles.editPill}
              activeOpacity={0.7}
            >
              <Text style={styles.editPillText}>{showHotelPicker ? 'Done' : 'Change'}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.selectedOptionBox}>
            <View style={styles.optionHeader}>
              <Text style={styles.optionName}>{selectedHotel.name}</Text>
              <Text style={styles.optionPrice}>₹{selectedHotel.pricePerNight} / night</Text>
            </View>
            <Text style={styles.optionRoute}>{selectedHotel.location}</Text>
            <Text style={styles.optionTiming}>
              {roomsCount} {roomsCount === 1 ? 'Room' : 'Rooms'} for {nights} {nights === 1 ? 'Night' : 'Nights'} · {selectedHotel.roomType}
            </Text>
          </View>

          {/* Interactive Hotel Options Picker */}
          {showHotelPicker && (
            <View style={styles.pickerContainer}>
              <Text style={styles.pickerTitle}>Select Bhawan or Hotel:</Text>
              {ACCOMMODATION_CATALOGUE.map((h) => {
                const isCur = h.id === selectedHotel.id;
                return (
                  <TouchableOpacity
                    key={h.id}
                    style={[styles.pickerItem, isCur && styles.pickerItemActive]}
                    onPress={() => {
                      setSelectedHotel(h);
                      setShowHotelPicker(false);
                    }}
                    activeOpacity={0.8}
                  >
                    <View style={styles.pickerItemInfo}>
                      <Text style={[styles.pickerItemName, isCur && styles.pickerItemNameActive]}>
                        {h.name}
                      </Text>
                      <Text style={styles.pickerItemSub}>{h.location} · {h.roomType}</Text>
                    </View>
                    <Text style={styles.pickerItemPrice}>₹{h.pricePerNight}/n</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
        </View>

        {/* 6. Detailed Itemized Budget Breakdown */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>💰 Detailed Budget Breakdown</Text>
          </View>

          <View style={styles.budgetTable}>
            <View style={styles.budgetRow}>
              <Text style={styles.budgetCategory}>Transit ({selectedTransport.name} × {pax})</Text>
              <Text style={styles.budgetValue}>₹{transportCost.toLocaleString('en-IN')}</Text>
            </View>

            <View style={styles.budgetRow}>
              <Text style={styles.budgetCategory}>Lodging ({selectedHotel.name} × {nights}N)</Text>
              <Text style={styles.budgetValue}>₹{hotelCost.toLocaleString('en-IN')}</Text>
            </View>

            {ascentCost > 0 && (
              <View style={styles.budgetRow}>
                <Text style={styles.budgetCategory}>Ascent ({selectedAscent.name} × {pax})</Text>
                <Text style={styles.budgetValue}>₹{ascentCost.toLocaleString('en-IN')}</Text>
              </View>
            )}

            <View style={styles.budgetRow}>
              <Text style={styles.budgetCategory}>Meals & Refreshment Estimate</Text>
              <Text style={styles.budgetValue}>₹{mealsCost.toLocaleString('en-IN')}</Text>
            </View>

            <View style={[styles.budgetRow, styles.budgetGrandTotalRow]}>
              <View>
                <Text style={styles.grandTotalLabel}>ESTIMATED TOTAL BUDGET</Text>
                <Text style={styles.grandTotalSub}>₹{perPersonCost.toLocaleString('en-IN')} per devotee</Text>
              </View>
              <Text style={styles.grandTotalValue}>₹{grandTotal.toLocaleString('en-IN')}</Text>
            </View>
          </View>
        </View>

        {/* 7. Action Button: Proceed Directly with Booking Wizard */}
        <TouchableOpacity
          style={styles.bookingProceedBtn}
          onPress={handleProceedBooking}
          activeOpacity={0.85}
          accessibilityLabel="Proceed to Guided Booking Wizard"
        >
          <TicketIcon size={18} color="#FFFFFF" strokeWidth={2.4} />
          <Text style={styles.bookingProceedText}>Proceed with Booking</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.surfaceWarm || '#F7F1EB',
  },
  container: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  overviewCard: {
    backgroundColor: colors.surfaceWhite || '#FFFFFF',
    borderWidth: 1.2,
    borderColor: colors.borderDefault || '#E9DED6',
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 5,
    elevation: 2,
  },
  overviewBadgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  sacredBadge: {
    backgroundColor: 'rgba(84, 21, 45, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  sacredBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    letterSpacing: 0.4,
  },
  nightsBadge: {
    fontSize: 11.5,
    fontWeight: '700',
    color: colors.champagneTaupe || '#A3826C',
  },
  destinationHeading: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    marginBottom: 10,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  metaChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.softPlum || '#F0E3E7',
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 8,
  },
  metaChipText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: colors.royalPlum || '#54152D',
  },
  sectionCard: {
    backgroundColor: colors.surfaceWhite || '#FFFFFF',
    borderWidth: 1,
    borderColor: colors.borderDefault || '#E9DED6',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionHeaderBetween: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 14.5,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
  },
  editPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: colors.softPlum || '#F0E3E7',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.borderDefault || '#E9DED6',
  },
  editPillText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
  },
  dayCard: {
    backgroundColor: '#FAF7F5',
    borderWidth: 1,
    borderColor: colors.borderSubtle || '#F5ECE6',
    borderRadius: 10,
    padding: 10,
    marginBottom: 10,
  },
  dayHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  dayBadge: {
    backgroundColor: colors.royalPlum || '#54152D',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  dayBadgeText: {
    color: '#FFFFFF',
    fontSize: 9.5,
    fontWeight: '800',
  },
  dayThemeText: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
    flex: 1,
  },
  activityRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginTop: 4,
    paddingLeft: 4,
  },
  activityDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.champagneTaupe || '#A3826C',
    marginTop: 6,
  },
  activityBody: {
    flex: 1,
  },
  activityTime: {
    fontSize: 10.5,
    fontWeight: '700',
    color: colors.champagneTaupe || '#A3826C',
    marginBottom: 1,
  },
  activityDesc: {
    fontSize: 12.5,
    lineHeight: 18,
    color: colors.textPrimary || '#30272A',
  },
  subsectionLabel: {
    fontSize: 11.5,
    fontWeight: '700',
    color: colors.champagneTaupe || '#A3826C',
    marginBottom: 8,
  },
  sightseeingList: {
    gap: 6,
    marginBottom: 8,
  },
  feasibleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  feasibleText: {
    fontSize: 13,
    color: colors.textPrimary || '#30272A',
  },
  infeasibleBox: {
    backgroundColor: '#FFF9E6',
    borderWidth: 1,
    borderColor: '#FFEEBA',
    borderRadius: 8,
    padding: 10,
    marginTop: 8,
  },
  infeasibleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  infeasibleHeading: {
    fontSize: 12,
    fontWeight: '700',
    color: '#856404',
  },
  infeasibleItem: {
    fontSize: 11.5,
    color: '#856404',
    lineHeight: 16,
  },
  selectedOptionBox: {
    backgroundColor: colors.softPlum || '#F0E3E7',
    borderRadius: 10,
    padding: 12,
  },
  optionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  optionName: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    flex: 1,
  },
  optionPrice: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
  },
  optionRoute: {
    fontSize: 12,
    color: colors.textPrimary || '#30272A',
    marginBottom: 2,
  },
  optionTiming: {
    fontSize: 11,
    color: colors.textSecondary || '#736B66',
  },
  pickerContainer: {
    marginTop: 10,
    backgroundColor: '#FAF7F5',
    borderRadius: 10,
    padding: 8,
    gap: 6,
  },
  pickerTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.champagneTaupe || '#A3826C',
    marginBottom: 4,
  },
  pickerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: colors.borderDefault || '#E9DED6',
    borderRadius: 8,
    padding: 8,
  },
  pickerItemActive: {
    borderColor: colors.royalPlum || '#54152D',
    backgroundColor: colors.softPlum || '#F0E3E7',
  },
  pickerItemInfo: {
    flex: 1,
  },
  pickerItemName: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.textPrimary || '#30272A',
  },
  pickerItemNameActive: {
    color: colors.royalPlum || '#54152D',
  },
  pickerItemSub: {
    fontSize: 10.5,
    color: colors.textSecondary || '#736B66',
  },
  pickerItemPrice: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.royalPlum || '#54152D',
  },
  budgetTable: {
    gap: 8,
  },
  budgetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle || '#F5ECE6',
  },
  budgetCategory: {
    fontSize: 12.5,
    color: colors.textPrimary || '#30272A',
  },
  budgetValue: {
    fontSize: 12.5,
    fontWeight: '600',
    color: colors.textPrimary || '#30272A',
  },
  budgetGrandTotalRow: {
    marginTop: 6,
    paddingTop: 8,
    borderBottomWidth: 0,
    backgroundColor: colors.softPlum || '#F0E3E7',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 10,
  },
  grandTotalLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
    letterSpacing: 0.4,
  },
  grandTotalSub: {
    fontSize: 10,
    color: colors.textSecondary || '#736B66',
  },
  grandTotalValue: {
    fontSize: 16.5,
    fontWeight: '800',
    color: colors.royalPlum || '#54152D',
  },
  bookingProceedBtn: {
    backgroundColor: colors.royalPlum || '#54152D',
    borderRadius: 12,
    paddingVertical: 13,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 8,
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 5,
    elevation: 3,
  },
  bookingProceedText: {
    color: '#FFFFFF',
    fontSize: 14.5,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
});