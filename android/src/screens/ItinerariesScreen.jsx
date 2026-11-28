import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  Modal,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import Header from '../components/Header';
import {
  MapIcon,
  CalendarIcon,
  UserIcon,
  PlusIcon,
  RefreshIcon,
  SearchIcon,
  EditIcon,
  ShareIcon,
  TrashIcon,
  ClockIcon,
  ArrowRightIcon,
} from '../components/Icons';
import {
  listItineraries,
  upsertItinerary,
  deleteItineraryById,
  acceptItineraryInvite,
  getAuthMe,
} from '../services/api';

function RoleChip({ role }) {
  const r = String(role || 'VIEWER').toUpperCase();
  const bg = r === 'OWNER' ? colors.royalPlum : r === 'EDITOR' ? '#D1FAE5' : '#F2EAE4';
  const fg = r === 'OWNER' ? '#FFFFFF' : r === 'EDITOR' ? '#065F46' : colors.royalPlum;
  return (
    <View style={[styles.roleChip, { backgroundColor: bg }]}>
      <Text style={[styles.roleChipText, { color: fg }]}>{r}</Text>
    </View>
  );
}

export default function ItinerariesScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [inviteToken, setInviteToken] = useState('');

  // Create modal
  const [createVisible, setCreateVisible] = useState(false);
  const [newTitle, setNewTitle] = useState('Sacred Vaishno Devi Yatra');
  const [newDays, setNewDays] = useState('4');
  const [newPax, setNewPax] = useState('2');
  const [newStartDate, setNewStartDate] = useState('');

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const me = await getAuthMe();
      if (!me?.authenticated || !me?.user) {
        setUser(null);
        setItems([]);
        return;
      }
      setUser(me.user);
      const res = await listItineraries();
      setItems(res?.itineraries || []);
    } catch (err) {
      setError(err?.message || 'Unable to load saved itineraries.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const unsub = navigation?.addListener?.('focus', () => loadData());
    return unsub;
  }, [loadData, navigation]);

  const handleOpenItinerary = (item, openEditor = false, openShare = false) => {
    navigation.navigate('Itinerary', {
      savedItinerary: item,
      itineraryId: item.itinerary_id,
      destination: item.destination || item.title,
      duration: item.duration_days,
      pax: item.travellers_count,
      startDate: item.start_date,
      itinerary: item.data,
      initialEditMode: openEditor,
      initialShareModal: openShare,
    });
  };

  const handleDelete = (item) => {
    Alert.alert(
      'Delete Itinerary',
      `Permanently delete "${item.title}"? Shared access will also be removed.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteItineraryById(item.itinerary_id);
              loadData();
            } catch (err) {
              Alert.alert('Delete Failed', err?.message || 'Unable to delete itinerary.');
            }
          },
        },
      ]
    );
  };

  const handleCreate = async () => {
    const dur = Math.max(1, Math.min(90, parseInt(newDays, 10) || 4));
    const pax = Math.max(1, parseInt(newPax, 10) || 2);
    const days = Array.from({ length: dur }, (_, idx) => {
      const dNum = idx + 1;
      return {
        day_number: dNum,
        title:
          dNum === 1
            ? 'Arrival at Katra & Yatra Registration'
            : dNum === 2
            ? 'Sacred Trek & Mata Vaishno Devi Darshan'
            : dNum === dur
            ? 'Morning Prasad & Departure'
            : `Day ${dNum} Local Pilgrimage Excursion`,
        activities:
          dNum === 2
            ? [
                { time: '06:00 AM', duration: '5 hrs', activity: 'Sacred Bhawan trek via Ardhkuwari Cave', place: 'Ardhkuwari Cave', notes: '' },
                { time: '02:00 PM', duration: '2 hrs', activity: 'Bhawan Darshan & Bhairavnath Temple', place: 'Bhairavnath Temple', notes: '' },
              ]
            : [{ time: '09:30 AM', duration: '2 hrs', activity: `Day ${dNum} scheduled pilgrimage program`, notes: '' }],
      };
    });

    try {
      const res = await upsertItinerary({
        title: newTitle.trim() || 'Sacred Vaishno Devi Yatra',
        itinerary: {
          title: newTitle.trim() || 'Sacred Vaishno Devi Yatra',
          destination: 'Shri Mata Vaishno Devi Shrine',
          start_date: newStartDate.trim() || undefined,
          duration_days: dur,
          travellers_count: pax,
          days,
        },
      });
      setCreateVisible(false);
      await loadData();
      if (res?.itinerary) {
        handleOpenItinerary(res.itinerary, false, false);
      }
    } catch (err) {
      Alert.alert('Create Failed', err?.message || 'Unable to create itinerary.');
    }
  };

  const handleJoinInvite = async () => {
    const clean = inviteToken.trim();
    if (!clean) return;
    try {
      const extracted = clean.includes('invite=') ? clean.split('invite=').pop().split('&')[0] : clean;
      const res = await acceptItineraryInvite(extracted);
      setInviteToken('');
      await loadData();
      if (res?.itinerary) {
        handleOpenItinerary(res.itinerary, false, false);
      }
    } catch (err) {
      Alert.alert('Invite Error', err?.message || 'Invalid, expired, or revoked invite token.');
    }
  };

  const filtered = items.filter((item) => {
    if (roleFilter === 'OWNER' && item.my_role !== 'OWNER') return false;
    if (roleFilter === 'SHARED' && item.my_role === 'OWNER') return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      String(item.title || '').toLowerCase().includes(q) ||
      String(item.destination || '').toLowerCase().includes(q) ||
      (item.destinations || []).some((d) => String(d).toLowerCase().includes(q))
    );
  });

  return (
    <View style={styles.screen}>
      <Header
        title="My Itineraries"
        subtitle="Saved Plans, Editing & Group Sharing"
        showBack={true}
        onBackPress={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Assistant'))}
      />

      <ScrollView
        style={styles.container}
        contentContainerStyle={[styles.content, { paddingBottom: Math.max(40, insets.bottom + 24) }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadData(true)} tintColor={colors.royalPlum} />}
      >
        {!user && !loading ? (
          <View style={styles.emptyCard}>
            <MapIcon size={34} color={colors.royalPlum} />
            <Text style={styles.emptyTitle}>Sign in to manage &amp; share itineraries</Text>
            <Text style={styles.emptySub}>
              Authenticate via Email OTP to save trips, customize individual days, and join shared family yatra links.
            </Text>
            <TouchableOpacity style={styles.primaryBtn} onPress={() => navigation.navigate('Auth')}>
              <Text style={styles.primaryBtnText}>Sign In with Email OTP</Text>
            </TouchableOpacity>
          </View>
        ) : loading ? (
          <View style={styles.centerBox}>
            <ActivityIndicator size="large" color={colors.royalPlum} />
            <Text style={styles.loadingText}>Loading your itineraries...</Text>
          </View>
        ) : (
          <>
            {error && (
              <View style={styles.errorBanner}>
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity onPress={() => loadData()}>
                  <Text style={styles.retryText}>Retry</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Search & Create Toolbar */}
            <View style={styles.toolbarRow}>
              <View style={styles.searchBox}>
                <SearchIcon size={15} color={colors.textSecondary} />
                <TextInput
                  style={styles.searchInput}
                  value={searchQuery}
                  onChangeText={setSearchQuery}
                  placeholder="Search itineraries or places..."
                  placeholderTextColor={colors.textSecondary}
                />
              </View>
              <TouchableOpacity style={styles.iconBtn} onPress={() => loadData(true)} accessibilityLabel="Refresh Itineraries">
                <RefreshIcon size={17} color={colors.royalPlum} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.createBtnSmall} onPress={() => setCreateVisible(true)}>
                <PlusIcon size={16} color="#FFFFFF" />
                <Text style={styles.createBtnSmallText}>New</Text>
              </TouchableOpacity>
            </View>

            {/* Filter Chips */}
            <View style={styles.filterRow}>
              {['ALL', 'OWNER', 'SHARED'].map((f) => (
                <TouchableOpacity
                  key={f}
                  style={[styles.filterPill, roleFilter === f && styles.filterPillActive]}
                  onPress={() => setRoleFilter(f)}
                >
                  <Text style={[styles.filterText, roleFilter === f && styles.filterTextActive]}>
                    {f === 'ALL' ? 'All Trips' : f === 'OWNER' ? 'Owned' : 'Shared with Me'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Join via Invite Link / Token */}
            <View style={styles.inviteJoinRow}>
              <TextInput
                style={styles.inviteInput}
                value={inviteToken}
                onChangeText={setInviteToken}
                placeholder="Paste share invite token or URL..."
                placeholderTextColor={colors.textSecondary}
              />
              <TouchableOpacity style={styles.joinBtn} onPress={handleJoinInvite}>
                <Text style={styles.joinBtnText}>Join</Text>
              </TouchableOpacity>
            </View>

            {filtered.length === 0 ? (
              <View style={styles.emptyCard}>
                <CalendarIcon size={32} color={colors.royalPlum} />
                <Text style={styles.emptyTitle}>No saved itineraries yet</Text>
                <Text style={styles.emptySub}>Create your first structured pilgrimage plan or save one from AI Chat.</Text>
                <TouchableOpacity style={styles.primaryBtn} onPress={() => setCreateVisible(true)}>
                  <Text style={styles.primaryBtnText}>Create Itinerary</Text>
                </TouchableOpacity>
              </View>
            ) : (
              filtered.map((item) => (
                <View key={item.itinerary_id} style={styles.card}>
                  <View style={styles.cardHeader}>
                    <RoleChip role={item.my_role} />
                    <Text style={styles.sharingText}>{item.sharing_status} · v{item.revision}</Text>
                  </View>
                  <Text style={styles.cardTitle}>{item.title}</Text>
                  <Text style={styles.metaText}>
                    {(item.destinations || []).slice(0, 3).join(', ') || item.destination}
                  </Text>
                  <View style={styles.metaLine}>
                    <CalendarIcon size={13} color={colors.royalPlum} />
                    <Text style={styles.metaLineText}>
                      {item.start_date || 'Flexible Dates'} · {item.duration_days} Days
                    </Text>
                    <UserIcon size={13} color={colors.royalPlum} />
                    <Text style={styles.metaLineText}>{item.travellers_count} Travellers</Text>
                  </View>
                  <View style={styles.metaLine}>
                    <ClockIcon size={12} color={colors.textSecondary} />
                    <Text style={styles.updatedText}>
                      Updated {new Date(item.updated_at).toLocaleDateString()}
                    </Text>
                  </View>

                  <View style={styles.cardActions}>
                    <TouchableOpacity style={styles.viewBtn} onPress={() => handleOpenItinerary(item, false, false)}>
                      <Text style={styles.viewBtnText}>View</Text>
                      <ArrowRightIcon size={13} color="#FFFFFF" />
                    </TouchableOpacity>
                    {item.can_edit && (
                      <TouchableOpacity style={styles.actionPill} onPress={() => handleOpenItinerary(item, true, false)}>
                        <EditIcon size={13} color={colors.royalPlum} />
                        <Text style={styles.actionPillText}>Edit</Text>
                      </TouchableOpacity>
                    )}
                    {item.can_manage_shares && (
                      <TouchableOpacity style={styles.actionPill} onPress={() => handleOpenItinerary(item, false, true)}>
                        <ShareIcon size={13} color={colors.royalPlum} />
                        <Text style={styles.actionPillText}>Share</Text>
                      </TouchableOpacity>
                    )}
                    {item.can_delete && (
                      <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDelete(item)}>
                        <TrashIcon size={14} color="#991B1B" />
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              ))
            )}
          </>
        )}
      </ScrollView>

      {/* Create Itinerary Modal */}
      <Modal visible={createVisible} transparent animationType="slide" onRequestClose={() => setCreateVisible(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={[styles.modalBackdrop, { paddingBottom: Math.max(18, insets.bottom + 14) }]}
        >
          <View style={[styles.modalCard, { maxHeight: '85%' }]}>
            <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
              <Text style={styles.modalTitle}>Create Itinerary</Text>
              <TextInput style={styles.modalInput} value={newTitle} onChangeText={setNewTitle} placeholder="Trip Title" />
              <View style={styles.modalRow}>
                <TextInput style={[styles.modalInput, { flex: 1 }]} value={newDays} onChangeText={setNewDays} keyboardType="numeric" placeholder="Days" />
                <TextInput style={[styles.modalInput, { flex: 1 }]} value={newPax} onChangeText={setNewPax} keyboardType="numeric" placeholder="Travellers" />
              </View>
              <TextInput style={styles.modalInput} value={newStartDate} onChangeText={setNewStartDate} placeholder="Start Date YYYY-MM-DD (optional)" />
              <View style={styles.modalActions}>
                <TouchableOpacity style={styles.cancelBtn} onPress={() => setCreateVisible(false)}>
                  <Text style={styles.cancelBtnText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.primaryBtn} onPress={handleCreate}>
                  <Text style={styles.primaryBtnText}>Create</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.surfaceWarm || '#F7F1EB' },
  container: { flex: 1 },
  content: { padding: 14, paddingBottom: 40 },
  centerBox: { padding: 36, alignItems: 'center' },
  loadingText: { marginTop: 10, color: colors.textSecondary, fontWeight: '600' },
  errorBanner: { backgroundColor: '#FEE2E2', padding: 10, borderRadius: 10, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between' },
  errorText: { color: '#991B1B', fontWeight: '600', flex: 1 },
  retryText: { color: '#991B1B', fontWeight: '800', marginLeft: 8 },
  toolbarRow: { flexDirection: 'row', gap: 8, marginBottom: 10, alignItems: 'center' },
  searchBox: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#FFFFFF', borderRadius: 10, borderWidth: 1, borderColor: '#E9DED6', paddingHorizontal: 10, height: 40 },
  searchInput: { flex: 1, fontSize: 13.5, color: '#30272A' },
  iconBtn: { width: 40, height: 40, borderRadius: 10, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E9DED6', alignItems: 'center', justifyContent: 'center' },
  createBtnSmall: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.royalPlum || '#54152D', paddingHorizontal: 12, height: 40, borderRadius: 10 },
  createBtnSmallText: { color: '#FFFFFF', fontWeight: '800', fontSize: 13 },
  filterRow: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  filterPill: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: '#EFE5DD' },
  filterPillActive: { backgroundColor: colors.royalPlum || '#54152D' },
  filterText: { fontSize: 12, fontWeight: '700', color: colors.royalPlum || '#54152D' },
  filterTextActive: { color: '#FFFFFF' },
  inviteJoinRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  inviteInput: { flex: 1, backgroundColor: '#FFFFFF', borderRadius: 10, borderWidth: 1, borderColor: '#E9DED6', paddingHorizontal: 10, height: 38, fontSize: 12.5 },
  joinBtn: { backgroundColor: '#FFFFFF', borderWidth: 1.2, borderColor: colors.royalPlum || '#54152D', paddingHorizontal: 14, borderRadius: 10, justifyContent: 'center' },
  joinBtnText: { color: colors.royalPlum || '#54152D', fontWeight: '800', fontSize: 12.5 },
  emptyCard: { backgroundColor: '#FFFFFF', borderRadius: 14, borderWidth: 1.2, borderColor: '#E9DED6', padding: 24, alignItems: 'center', marginTop: 10 },
  emptyTitle: { fontSize: 16, fontWeight: '800', color: colors.royalPlum || '#54152D', marginTop: 10, marginBottom: 6, textAlign: 'center' },
  emptySub: { fontSize: 13, color: colors.textSecondary, textAlign: 'center', marginBottom: 16 },
  primaryBtn: { backgroundColor: colors.royalPlum || '#54152D', paddingHorizontal: 18, paddingVertical: 10, borderRadius: 10 },
  primaryBtnText: { color: '#FFFFFF', fontWeight: '800', fontSize: 13.5 },
  card: { backgroundColor: '#FFFFFF', borderRadius: 14, borderWidth: 1.2, borderColor: '#E9DED6', padding: 14, marginBottom: 12 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  roleChip: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  roleChipText: { fontSize: 10, fontWeight: '800' },
  sharingText: { fontSize: 11.5, fontWeight: '600', color: colors.textSecondary },
  cardTitle: { fontSize: 16, fontWeight: '800', color: colors.royalPlum || '#54152D', marginBottom: 4 },
  metaText: { fontSize: 12.5, color: '#5D4B4F', marginBottom: 6 },
  metaLine: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  metaLineText: { fontSize: 12, color: '#30272A', fontWeight: '600', marginRight: 8 },
  updatedText: { fontSize: 11.5, color: colors.textSecondary },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#EFE5DD' },
  viewBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, backgroundColor: colors.royalPlum || '#54152D', paddingVertical: 8, borderRadius: 8 },
  viewBtnText: { color: '#FFFFFF', fontWeight: '800', fontSize: 12.5 },
  actionPill: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#F2EAE4', paddingHorizontal: 10, paddingVertical: 8, borderRadius: 8 },
  actionPillText: { color: colors.royalPlum || '#54152D', fontWeight: '700', fontSize: 12 },
  deleteBtn: { backgroundColor: '#FEE2E2', paddingHorizontal: 10, paddingVertical: 8, borderRadius: 8, justifyContent: 'center' },
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(42, 10, 24, 0.5)', justifyContent: 'center', padding: 18 },
  modalCard: { backgroundColor: '#FFFCF9', borderRadius: 16, padding: 18 },
  modalTitle: { fontSize: 17, fontWeight: '800', color: colors.royalPlum || '#54152D', marginBottom: 12 },
  modalInput: { borderWidth: 1, borderColor: '#E9DED6', borderRadius: 10, padding: 10, marginBottom: 10, backgroundColor: '#FFFFFF' },
  modalRow: { flexDirection: 'row', gap: 8 },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 4 },
  cancelBtn: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#E9DED6' },
  cancelBtnText: { fontWeight: '700', color: '#30272A' },
});

