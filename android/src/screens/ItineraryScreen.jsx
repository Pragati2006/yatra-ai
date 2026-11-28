import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Modal,
  TextInput,
  Share,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Clipboard from 'expo-clipboard';
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
  EditIcon,
  ShareIcon,
  UndoIcon,
  TrashIcon,
  CopyIcon,
} from '../components/Icons';
import {
  REALISTIC_TRANSPORTS,
  ASCENT_MODES,
  ACCOMMODATION_CATALOGUE,
} from './BookingScreen';
import {
  upsertItinerary,
  getItineraryDetail,
  previewItineraryEdit,
  applyItineraryEdit,
  undoItineraryEdit,
  createItineraryInvite,
  listItineraryShares,
  updateItineraryMemberRole,
  revokeItineraryMember,
  revokeItineraryInvite,
} from '../services/api';

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
  const insets = useSafeAreaInsets();
  const params = route?.params || {};
  const req = params.request || params.recommendation?.profile || {};

  // Collaborative saved itinerary state (Phase 8.8.58)
  const [savedRecord, setSavedRecord] = useState(params.savedItinerary || null);
  const recData = savedRecord?.data || {};

  const destination =
    savedRecord?.destination ||
    recData.destination ||
    params.destination ||
    req.destination ||
    'Shri Mata Vaishno Devi Shrine';
  const duration = parseInt(
    savedRecord?.duration_days ||
      recData.duration_days ||
      (Array.isArray(recData.days) && recData.days.length) ||
      params.duration ||
      req.duration_days ||
      4,
    10
  );
  const nights = Math.max(1, duration - 1);
  const pax = parseInt(
    savedRecord?.travellers_count || recData.travellers_count || params.pax || req.pax || 2,
    10
  );
  const origin = recData.request?.origin || params.origin || req.origin || 'New Delhi';
  const initialStartDate =
    savedRecord?.start_date || recData.start_date || params.startDate || req.start_date || '2026-11-25';

  // Editable trip states
  const [startDate, setStartDate] = useState(initialStartDate);
  const lastSyncedRevRef = useRef(savedRecord ? `${savedRecord.itinerary_id}:${savedRecord.revision}` : null);
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

  const [editMode, setEditMode] = useState(Boolean(params.initialEditMode));
  const [selectedDayNum, setSelectedDayNum] = useState(1);
  const [editOp, setEditOp] = useState('regenerate_day');
  const [aiInstruction, setAiInstruction] = useState('');
  const [editPlace, setEditPlace] = useState('Baba Dhansar');
  const [editTime, setEditTime] = useState('02:30 PM');
  const [editDurStr, setEditDurStr] = useState('2 hrs');
  const [notesInput, setNotesInput] = useState('');
  const [durDaysInput, setDurDaysInput] = useState(String(duration));

  // Sync displayed fields cleanly when savedRecord loads or updates revision
  useEffect(() => {
    if (!savedRecord) return;
    const revKey = `${savedRecord.itinerary_id}:${savedRecord.revision}`;
    if (lastSyncedRevRef.current === revKey) return;
    lastSyncedRevRef.current = revKey;
    const syncedStart =
      savedRecord.start_date || savedRecord.data?.start_date || savedRecord.data?.request?.start_date;
    if (syncedStart) setStartDate(syncedStart);
    const syncedDur =
      savedRecord.duration_days || savedRecord.data?.duration_days || savedRecord.data?.days?.length;
    if (syncedDur) setDurDaysInput(String(syncedDur));
  }, [savedRecord]);
  const [previewState, setPreviewState] = useState(null);
  const [pendingPayload, setPendingPayload] = useState(null);
  const [confirmImpact, setConfirmImpact] = useState(false);

  // Sharing modal state
  const [shareVisible, setShareVisible] = useState(Boolean(params.initialShareModal));
  const [shareInfo, setShareInfo] = useState({ members: [], invites: [] });
  const [shareRole, setShareRole] = useState('VIEWER');
  const [latestInvite, setLatestInvite] = useState(null);

  useEffect(() => {
    const id = params.itineraryId || params.savedItinerary?.itinerary_id;
    if (id && !params.savedItinerary) {
      getItineraryDetail(id)
        .then((res) => {
          if (res?.itinerary) setSavedRecord(res.itinerary);
        })
        .catch(() => {});
    }
  }, [params.itineraryId, params.savedItinerary]);

  // Day-wise Schedule data
  const activeItinSource = savedRecord?.data || params.itinerary || params.recommendation?.itinerary || params.plan?.itinerary || null;
  const rawItin = activeItinSource;
  const itinDays = activeItinSource?.days || (Array.isArray(activeItinSource) ? activeItinSource : []);
  const myRole = savedRecord?.my_role || 'OWNER';
  const canEdit = savedRecord ? savedRecord.can_edit : true;
  const isOwner = savedRecord ? savedRecord.is_owner : true;

  const handleSaveToAccount = async () => {
    try {
      const daysPayload =
        itinDays && itinDays.length > 0
          ? itinDays
          : [
              { day_number: 1, title: 'Arrival at Katra Base Camp', activities: ['Hotel check-in & RFID card collection'] },
              { day_number: 2, title: 'Sacred Trek & Mata Vaishno Devi Darshan', activities: ['Trek via Ardhkuwari to Bhawan & Bhairavnath Temple'] },
            ];
      const res = await upsertItinerary({
        title: `${destination} (${duration} Days)`,
        itineraryId: savedRecord?.itinerary_id || null,
        sourceKey: params.sessionId ? `android-itin-${params.sessionId}` : null,
        itinerary: {
          title: `${destination} (${duration} Days)`,
          destination,
          start_date: startDate,
          duration_days: duration,
          travellers_count: pax,
          request: req,
          days: daysPayload,
        },
      });
      if (res?.itinerary) {
        setSavedRecord(res.itinerary);
        Alert.alert('Itinerary Saved', 'Saved to My Itineraries cleanly without duplicates.');
      }
    } catch (err) {
      Alert.alert('Sign In Required', err?.message || 'Sign in via Email OTP to save, edit, or share this itinerary.');
    }
  };

  const triggerEditPreview = async (explicitPayload = null) => {
    if (!savedRecord?.itinerary_id) {
      Alert.alert('Save First', 'Please tap "Save to Itineraries" before applying partial edits.');
      return;
    }
    const payload =
      explicitPayload ||
      (editOp === 'regenerate_day'
        ? { operation: 'regenerate_day', day_number: selectedDayNum, instruction: aiInstruction.trim() || undefined }
        : editOp === 'add_destination'
        ? { operation: 'add_destination', day_number: selectedDayNum, place: editPlace.trim(), time: editTime.trim(), duration: editDurStr.trim() }
        : editOp === 'update_preferences'
        ? { operation: 'update_preferences', day_number: selectedDayNum, preferences: { pace: 'relaxed' } }
        : editOp === 'update_notes'
        ? { operation: 'update_notes', day_number: selectedDayNum, notes: notesInput.trim() }
        : { operation: 'adjust_duration', duration_days: parseInt(durDaysInput, 10) || duration });
    try {
      setConfirmImpact(false);
      const res = await previewItineraryEdit(savedRecord.itinerary_id, payload);
      setPreviewState(res.preview);
      setPendingPayload(payload);
    } catch (err) {
      Alert.alert('Preview Error', err?.message || 'Unable to compute preview.');
    }
  };

  const handleApplyPreview = async () => {
    if (!savedRecord?.itinerary_id || !pendingPayload) return;
    try {
      const res = await applyItineraryEdit(savedRecord.itinerary_id, {
        ...pendingPayload,
        expected_revision: previewState?.expected_revision ?? savedRecord.revision,
        confirm_impact: Boolean(confirmImpact || !previewState?.requires_confirmation),
      });
      if (res?.itinerary) setSavedRecord(res.itinerary);
      setPreviewState(null);
      setPendingPayload(null);
    } catch (err) {
      Alert.alert('Update Conflict or Error', err?.message || 'Could not apply changes. Please refresh.');
    }
  };

  const handleUndo = async () => {
    if (!savedRecord?.itinerary_id) return;
    try {
      const res = await undoItineraryEdit(savedRecord.itinerary_id, savedRecord.revision);
      if (res?.itinerary) setSavedRecord(res.itinerary);
    } catch (err) {
      Alert.alert('Undo Failed', err?.message || 'No earlier edits to revert.');
    }
  };

  const openShares = async () => {
    if (!savedRecord?.itinerary_id) {
      Alert.alert('Save First', 'Save this itinerary before sharing with travel companions.');
      return;
    }
    setShareVisible(true);
    try {
      const res = await listItineraryShares(savedRecord.itinerary_id);
      setShareInfo({ members: res.members || [], invites: res.invites || [] });
    } catch (err) {
      setShareVisible(false);
      Alert.alert('Access Restricted', err?.message || 'Only the owner can manage sharing.');
    }
  };

  const handleCreateInvite = async () => {
    if (!savedRecord?.itinerary_id) return;
    try {
      const res = await createItineraryInvite(savedRecord.itinerary_id, { role: shareRole, expiresInHours: 72 });
      setLatestInvite(res.share);
      const updated = await listItineraryShares(savedRecord.itinerary_id);
      setShareInfo({ members: updated.members || [], invites: updated.invites || [] });
    } catch (err) {
      Alert.alert('Invite Error', err?.message || 'Could not generate invite.');
    }
  };

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
        contentContainerStyle={[styles.contentContainer, { paddingBottom: Math.max(40, insets.bottom + 24) }]}
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

          {/* Save / Partial Edit / Undo / Share Bar */}
          <View style={styles.collabToolbar}>
            {!savedRecord ? (
              <TouchableOpacity style={styles.collabPrimaryPill} onPress={handleSaveToAccount}>
                <CheckIcon size={13} color="#FFFFFF" />
                <Text style={styles.collabPrimaryText}>Save to Itineraries</Text>
              </TouchableOpacity>
            ) : (
              <>
                <View style={styles.roleBadgePill}>
                  <Text style={styles.roleBadgeText}>{myRole} · v{savedRecord.revision || 1}</Text>
                </View>
                {canEdit && (
                  <TouchableOpacity style={styles.collabActionPill} onPress={() => setEditMode((v) => !v)}>
                    <EditIcon size={13} color={colors.royalPlum} />
                    <Text style={styles.collabActionText}>{editMode ? 'Close Editor' : 'Smart Edit'}</Text>
                  </TouchableOpacity>
                )}
                {canEdit && savedRecord.can_undo && (
                  <TouchableOpacity style={styles.collabActionPill} onPress={handleUndo}>
                    <UndoIcon size={13} color={colors.royalPlum} />
                    <Text style={styles.collabActionText}>Undo</Text>
                  </TouchableOpacity>
                )}
                {isOwner && (
                  <TouchableOpacity style={styles.collabActionPill} onPress={openShares}>
                    <ShareIcon size={13} color={colors.royalPlum} />
                    <Text style={styles.collabActionText}>Share</Text>
                  </TouchableOpacity>
                )}
              </>
            )}
          </View>
        </View>

        {/* Smart Partial Editor Card (OWNER / EDITOR only) */}
        {savedRecord && canEdit && editMode && (
          <View style={styles.editorCard}>
            <Text style={styles.editorHeading}>Smart Partial Editor (Selected Day Only)</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
              <View style={{ flexDirection: 'row', gap: 6 }}>
                {(itinDays || []).map((d, i) => {
                  const dn = d.day_number || i + 1;
                  return (
                    <TouchableOpacity
                      key={`sel-day-${dn}`}
                      style={[styles.daySelectPill, selectedDayNum === dn && styles.daySelectPillActive]}
                      onPress={() => setSelectedDayNum(dn)}
                    >
                      <Text style={[styles.daySelectText, selectedDayNum === dn && { color: '#FFFFFF' }]}>Day {dn}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </ScrollView>

            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {[
                { key: 'regenerate_day', label: 'Regenerate Day' },
                { key: 'add_destination', label: 'Add Place' },
                { key: 'update_preferences', label: 'Relaxed Pace' },
                { key: 'update_notes', label: 'Day Note' },
                { key: 'adjust_duration', label: 'Trip Days' },
              ].map((op) => (
                <TouchableOpacity
                  key={op.key}
                  style={[styles.opPill, editOp === op.key && styles.opPillActive]}
                  onPress={() => setEditOp(op.key)}
                >
                  <Text style={[styles.opPillText, editOp === op.key && { color: '#FFFFFF' }]}>{op.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {editOp === 'regenerate_day' && (
              <TextInput
                style={styles.editorInput}
                value={aiInstruction}
                onChangeText={setAiInstruction}
                placeholder={`Describe change for Day ${selectedDayNum} only...`}
              />
            )}
            {editOp === 'add_destination' && (
              <>
                <TextInput style={styles.editorInput} value={editPlace} onChangeText={setEditPlace} placeholder="Place name (e.g. Baba Dhansar)" />
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <TextInput style={[styles.editorInput, { flex: 1 }]} value={editTime} onChangeText={setEditTime} placeholder="Time" />
                  <TextInput style={[styles.editorInput, { flex: 1 }]} value={editDurStr} onChangeText={setEditDurStr} placeholder="Duration" />
                </View>
              </>
            )}
            {editOp === 'update_notes' && (
              <TextInput style={styles.editorInput} value={notesInput} onChangeText={setNotesInput} placeholder="Enter notes for this day..." />
            )}
            {editOp === 'adjust_duration' && (
              <TextInput style={styles.editorInput} value={durDaysInput} onChangeText={setDurDaysInput} keyboardType="numeric" placeholder="Total trip days (1-90)" />
            )}

            <TouchableOpacity style={styles.previewEditBtn} onPress={() => triggerEditPreview()}>
              <Text style={styles.previewEditBtnText}>Preview Before &amp; After</Text>
            </TouchableOpacity>
          </View>
        )}

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

      {/* Before & After Preview Modal */}
      <Modal visible={Boolean(previewState)} transparent animationType="slide" onRequestClose={() => setPreviewState(null)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={[styles.modalBackdrop, { paddingBottom: Math.max(16, insets.bottom + 12) }]}
        >
          <View style={[styles.modalCard, { maxHeight: '88%' }]}>
            <Text style={styles.modalTitle}>Review Changes (Before &amp; After)</Text>
            <ScrollView style={{ maxHeight: 340 }}>
              {(previewState?.diff_summary || []).map((line, i) => (
                <Text key={`diff-${i}`} style={styles.diffBullet}>• {line}</Text>
              ))}
              {previewState?.impact_warning && (
                <View style={styles.impactWarnBox}>
                  <Text style={styles.impactWarnText}>{previewState.impact_warning}</Text>
                  <TouchableOpacity
                    style={styles.confirmRow}
                    onPress={() => setConfirmImpact((c) => !c)}
                  >
                    <Text style={styles.confirmCheckText}>{confirmImpact ? '[✓] ' : '[ ] '}Confirm removing impacted day(s)</Text>
                  </TouchableOpacity>
                </View>
              )}
              {(previewState?.after?.days || [])
                .filter((d) => !(previewState?.affected_days || []).length || previewState.affected_days.includes(d.day_number))
                .map((d) => (
                  <View key={`after-${d.day_number}`} style={styles.afterPreviewBox}>
                    <Text style={{ fontWeight: '800', color: colors.royalPlum }}>Updated Day {d.day_number}: {d.title}</Text>
                    {(d.activities || []).map((a, idx) => (
                      <Text key={`a-${idx}`} style={{ fontSize: 12, marginTop: 2 }}>
                        • {typeof a === 'string' ? a : `${a.time ? a.time + ' · ' : ''}${a.activity}`}
                      </Text>
                    ))}
                  </View>
                ))}
            </ScrollView>
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setPreviewState(null)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.applyBtn, previewState?.requires_confirmation && !confirmImpact && { opacity: 0.5 }]}
                disabled={Boolean(previewState?.requires_confirmation && !confirmImpact)}
                onPress={handleApplyPreview}
              >
                <Text style={styles.applyBtnText}>Apply Changes</Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Group Collaboration & Sharing Modal (OWNER only) */}
      <Modal visible={shareVisible} transparent animationType="slide" onRequestClose={() => setShareVisible(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={[styles.modalBackdrop, { paddingBottom: Math.max(16, insets.bottom + 12) }]}
        >
          <View style={[styles.modalCard, { maxHeight: '88%' }]}>
            <Text style={styles.modalTitle}>Group Sharing &amp; Access</Text>
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
              {['VIEWER', 'EDITOR'].map((r) => (
                <TouchableOpacity
                  key={r}
                  style={[styles.opPill, shareRole === r && styles.opPillActive]}
                  onPress={() => setShareRole(r)}
                >
                  <Text style={[styles.opPillText, shareRole === r && { color: '#FFFFFF' }]}>{r}</Text>
                </TouchableOpacity>
              ))}
              <TouchableOpacity style={styles.applyBtn} onPress={handleCreateInvite}>
                <Text style={styles.applyBtnText}>Create Invite</Text>
              </TouchableOpacity>
            </View>

            {latestInvite && (
              <View style={styles.inviteTokenBox}>
                <Text style={{ fontWeight: '700', color: '#065F46', fontSize: 12 }}>
                  Token ({latestInvite.role}): {latestInvite.invite_token}
                </Text>
                <View style={{ flexDirection: 'row', gap: 8, marginTop: 6 }}>
                  <TouchableOpacity
                    style={styles.opPill}
                    onPress={async () => {
                      await Clipboard.setStringAsync(latestInvite.invite_url || latestInvite.invite_token);
                      Alert.alert('Copied', 'Invite link copied to clipboard.');
                    }}
                  >
                    <CopyIcon size={12} color={colors.royalPlum} />
                    <Text style={styles.opPillText}>Copy</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.opPill}
                    onPress={() => Share.share({ message: `Join my Vaishno Devi Yatra itinerary: ${latestInvite.invite_url || latestInvite.invite_token}` })}
                  >
                    <ShareIcon size={12} color={colors.royalPlum} />
                    <Text style={styles.opPillText}>Share</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            <ScrollView style={{ maxHeight: 210 }}>
              <Text style={styles.sectionSubLabel}>Members ({shareInfo.members.length})</Text>
              {shareInfo.members.map((m) => (
                <View key={m.user_id} style={styles.memberRow}>
                  <Text style={{ fontSize: 12.5, flex: 1 }}>{m.masked_email} ({m.role})</Text>
                  {m.role !== 'OWNER' && (
                    <View style={{ flexDirection: 'row', gap: 6 }}>
                      <TouchableOpacity
                        style={styles.opPill}
                        onPress={async () => {
                          await updateItineraryMemberRole(savedRecord.itinerary_id, m.user_id, m.role === 'VIEWER' ? 'EDITOR' : 'VIEWER');
                          openShares();
                        }}
                      >
                        <Text style={styles.opPillText}>{m.role === 'VIEWER' ? 'Make Editor' : 'Make Viewer'}</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.opPill, { backgroundColor: '#FEE2E2' }]}
                        onPress={async () => {
                          await revokeItineraryMember(savedRecord.itinerary_id, m.user_id);
                          openShares();
                        }}
                      >
                        <TrashIcon size={12} color="#991B1B" />
                      </TouchableOpacity>
                    </View>
                  )}
                </View>
              ))}

              <Text style={[styles.sectionSubLabel, { marginTop: 8 }]}>Invites ({shareInfo.invites.length})</Text>
              {shareInfo.invites.map((inv) => (
                <View key={inv.invite_id} style={styles.memberRow}>
                  <Text style={{ fontSize: 12, flex: 1 }}>{inv.role} · {inv.status}</Text>
                  {inv.status === 'ACTIVE' && (
                    <TouchableOpacity
                      style={[styles.opPill, { backgroundColor: '#FEE2E2' }]}
                      onPress={async () => {
                        await revokeItineraryInvite(savedRecord.itinerary_id, inv.invite_id);
                        openShares();
                      }}
                    >
                      <Text style={{ fontSize: 11, color: '#991B1B', fontWeight: '700' }}>Revoke</Text>
                    </TouchableOpacity>
                  )}
                </View>
              ))}
            </ScrollView>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShareVisible(false)}>
                <Text style={styles.cancelBtnText}>Close</Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  collabToolbar: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  collabPrimaryPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: '#54152D', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999 },
  collabPrimaryText: { color: '#FFFFFF', fontSize: 12, fontWeight: '800' },
  roleBadgePill: { backgroundColor: '#54152D', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999 },
  roleBadgeText: { color: '#FFFFFF', fontSize: 11, fontWeight: '800' },
  collabActionPill: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#F2EAE4', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, borderWidth: 1, borderColor: '#E9DED6' },
  collabActionText: { color: '#54152D', fontSize: 11.5, fontWeight: '700' },
  editorCard: { backgroundColor: '#FAF5F0', borderWidth: 1.2, borderColor: '#D9C3B4', borderRadius: 14, padding: 12, marginBottom: 14 },
  editorHeading: { fontSize: 13.5, fontWeight: '800', color: '#54152D', marginBottom: 8 },
  daySelectPill: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E9DED6' },
  daySelectPillActive: { backgroundColor: '#54152D', borderColor: '#54152D' },
  daySelectText: { fontSize: 11.5, fontWeight: '700', color: '#54152D' },
  opPill: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E9DED6' },
  opPillActive: { backgroundColor: '#54152D', borderColor: '#54152D' },
  opPillText: { fontSize: 11.5, fontWeight: '700', color: '#54152D' },
  editorInput: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E9DED6', borderRadius: 10, padding: 9, marginBottom: 8, fontSize: 13 },
  previewEditBtn: { backgroundColor: '#54152D', paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  previewEditBtnText: { color: '#FFFFFF', fontWeight: '800', fontSize: 13 },
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(42, 10, 24, 0.5)', justifyContent: 'center', padding: 16 },
  modalCard: { backgroundColor: '#FFFCF9', borderRadius: 16, padding: 16 },
  modalTitle: { fontSize: 16.5, fontWeight: '800', color: '#54152D', marginBottom: 10 },
  diffBullet: { fontSize: 12.5, color: '#30272A', marginBottom: 4 },
  impactWarnBox: { backgroundColor: '#FEF3C7', padding: 10, borderRadius: 10, marginVertical: 6 },
  impactWarnText: { fontSize: 12, color: '#92400E', fontWeight: '700', marginBottom: 4 },
  confirmRow: { paddingVertical: 4 },
  confirmCheckText: { fontSize: 12, fontWeight: '800', color: '#92400E' },
  afterPreviewBox: { backgroundColor: '#F2EAE4', padding: 10, borderRadius: 10, marginTop: 6 },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 12 },
  cancelBtn: { paddingHorizontal: 14, paddingVertical: 9, borderRadius: 10, borderWidth: 1, borderColor: '#E9DED6' },
  cancelBtnText: { fontWeight: '700', color: '#30272A' },
  applyBtn: { paddingHorizontal: 14, paddingVertical: 9, borderRadius: 10, backgroundColor: '#54152D' },
  applyBtnText: { color: '#FFFFFF', fontWeight: '800', fontSize: 12.5 },
  inviteTokenBox: { backgroundColor: '#D1FAE5', padding: 10, borderRadius: 10, marginBottom: 10 },
  sectionSubLabel: { fontSize: 11.5, fontWeight: '800', color: '#54152D', marginBottom: 4 },
  memberRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#EFE5DD' },
});