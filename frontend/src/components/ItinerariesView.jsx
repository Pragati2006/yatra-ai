import React, { useState, useEffect, useCallback } from 'react';
import {
  Map,
  CalendarDays,
  Users,
  Clock,
  Edit3,
  Trash2,
  Share2,
  Eye,
  Plus,
  RefreshCw,
  Search,
  RotateCcw,
  Sparkles,
  Check,
  X,
  AlertTriangle,
  Copy,
  Shield,
  ArrowLeft,
  Ticket,
  Link as LinkIcon,
  FileText,
} from 'lucide-react';
import {
  listItineraries,
  upsertItinerary,
  getItineraryDetail,
  deleteItineraryById,
  previewItineraryEdit,
  applyItineraryEdit,
  undoItineraryEdit,
  createItineraryInvite,
  listItineraryShares,
  updateItineraryMemberRole,
  revokeItineraryMember,
  revokeItineraryInvite,
  acceptItineraryInvite,
} from '../services/api';

const PLACE_SUGGESTIONS = [
  'Ardhkuwari Cave',
  'Bhairavnath Temple',
  'Banganga Temple',
  'Charan Paduka',
  'Baba Dhansar',
  'Nau Devi Cave Temple',
  'Patnitop',
  'Shiv Khori',
  'Raghunath Temple',
  'Bahu Fort',
  'Mansar Lake',
];

function formatActLine(act) {
  if (!act) return { time: '', duration: '', activity: '', notes: '' };
  if (typeof act === 'string') return { time: '', duration: '', activity: act, notes: '' };
  return {
    time: act.time || act.slot || '',
    duration: act.duration || '',
    activity: act.activity || act.description || act.place || '',
    notes: act.notes || '',
  };
}

function RoleBadge({ role }) {
  const norm = String(role || 'VIEWER').toUpperCase();
  const palette =
    norm === 'OWNER'
      ? { bg: '#54152D', fg: '#FFFFFF' }
      : norm === 'EDITOR'
      ? { bg: '#D1FAE5', fg: '#065F46' }
      : { bg: '#F2EAE4', fg: '#54152D' };
  return (
    <span
      data-testid={`role-badge-${norm.toLowerCase()}`}
      style={{
        fontSize: '0.68rem',
        fontWeight: 800,
        padding: '2px 8px',
        borderRadius: '999px',
        background: palette.bg,
        color: palette.fg,
        letterSpacing: '0.04em',
      }}
    >
      {norm}
    </span>
  );
}

export default function ItinerariesView({
  user = null,
  onOpenAuthModal,
  onReturnToAssistant,
  onProceedToBooking,
  initialItineraryId = null,
  pendingInviteToken = null,
  onInviteHandled = null,
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');

  const [selectedId, setSelectedId] = useState(initialItineraryId || null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Delete confirmation modal
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTitle, setCreateTitle] = useState('Sacred Vaishno Devi Yatra');
  const [createDays, setCreateDays] = useState(4);
  const [createPax, setCreatePax] = useState(2);
  const [createStartDate, setCreateStartDate] = useState('');

  // Join via invite modal
  const [inviteInput, setInviteInput] = useState(pendingInviteToken || '');
  const [inviteNotice, setInviteNotice] = useState(null);

  // Smart Partial Editor state
  const [isEditing, setIsEditing] = useState(false);
  const [activeDayNum, setActiveDayNum] = useState(1);
  const [editOp, setEditOp] = useState('regenerate_day');
  const [aiInstruction, setAiInstruction] = useState('');
  const [addPlace, setAddPlace] = useState('Baba Dhansar');
  const [addTime, setAddTime] = useState('02:30 PM');
  const [addDuration, setAddDuration] = useState('2 hrs');
  const [targetActIdx, setTargetActIdx] = useState(0);
  const [replacePlace, setReplacePlace] = useState('Patnitop');
  const [editTime, setEditTime] = useState('09:00 AM');
  const [editDuration, setEditDuration] = useState('2 hrs');
  const [dayPace, setDayPace] = useState('relaxed');
  const [notesDraft, setNotesDraft] = useState('');
  const [notesScope, setNotesScope] = useState('day'); // 'day' | 'trip'
  const [newDurationDays, setNewDurationDays] = useState(4);
  const [metaTitle, setMetaTitle] = useState('');
  const [metaStartDate, setMetaStartDate] = useState('');
  const [metaPax, setMetaPax] = useState(2);

  // Before / After Preview modal state
  const [previewData, setPreviewData] = useState(null);
  const [pendingPayload, setPendingPayload] = useState(null);
  const [confirmImpactChecked, setConfirmImpactChecked] = useState(false);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState(null);

  // Collaboration / Sharing panel state
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareData, setShareData] = useState({ members: [], invites: [] });
  const [shareRole, setShareRole] = useState('VIEWER');
  const [shareExpiryHours, setShareExpiryHours] = useState(72);
  const [latestInvite, setLatestInvite] = useState(null);
  const [shareBusy, setShareBusy] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const loadList = useCallback(async () => {
    if (!user) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await listItineraries();
      setItems(res?.itineraries || []);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Unable to load saved itineraries.');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const loadDetail = useCallback(async (id) => {
    if (!id || !user) return;
    setDetailLoading(true);
    setEditError(null);
    try {
      const res = await getItineraryDetail(id);
      const item = res?.itinerary || null;
      setSelectedDetail(item);
      if (item) {
        setMetaTitle(item.title || '');
        setMetaStartDate(item.start_date || '');
        setMetaPax(item.travellers_count || 2);
        setNewDurationDays(item.duration_days || item.data?.days?.length || 4);
      }
    } catch (err) {
      setEditError(err?.response?.data?.detail || 'Failed to load itinerary details.');
    } finally {
      setDetailLoading(false);
    }
  }, [user]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    if (initialItineraryId && user) {
      setSelectedId(initialItineraryId);
      loadDetail(initialItineraryId);
    }
  }, [initialItineraryId, user, loadDetail]);

  const handleAcceptInviteToken = useCallback(async (rawToken) => {
    const clean = String(rawToken || '').trim();
    if (!clean) return;
    if (!user) {
      onOpenAuthModal?.();
      return;
    }
    setError(null);
    setInviteNotice(null);
    try {
      const tokenExtracted = clean.includes('invite=') ? new URLSearchParams(clean.split('?')[1]).get('invite') || clean : clean;
      const res = await acceptItineraryInvite(tokenExtracted);
      const joined = res?.itinerary;
      setInviteInput('');
      setInviteNotice('Successfully joined shared itinerary.');
      await loadList();
      if (joined?.itinerary_id) {
        setSelectedId(joined.itinerary_id);
        setSelectedDetail(joined);
      }
      onInviteHandled?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Invalid, expired, or revoked invitation link.');
      onInviteHandled?.();
    }
  }, [user, onOpenAuthModal, loadList, onInviteHandled]);

  useEffect(() => {
    if (pendingInviteToken && user) {
      handleAcceptInviteToken(pendingInviteToken);
    }
  }, [pendingInviteToken, user, handleAcceptInviteToken]);

  const handleCreateItinerary = async (e) => {
    e.preventDefault();
    if (!user) {
      onOpenAuthModal?.();
      return;
    }
    const dur = Math.max(1, Math.min(90, Number(createDays) || 4));
    const days = Array.from({ length: dur }, (_, idx) => {
      const dNum = idx + 1;
      if (dNum === 1) {
        return {
          day_number: 1,
          title: 'Arrival at Katra & Yatra Parchi Registration',
          activities: [
            { time: '10:00 AM', duration: '2 hrs', activity: 'Check-in at Katra hotel & RFID registration', place: 'Banganga Temple', notes: '' },
            { time: '04:00 PM', duration: '1.5 hrs', activity: 'Darshani Deodi viewpoint walk & local bazaar', place: 'Darshani Deodi', notes: '' },
          ],
        };
      }
      if (dNum === 2) {
        return {
          day_number: 2,
          title: 'Holy Mata Vaishno Devi Trek & Bhawan Darshan',
          activities: [
            { time: '06:00 AM', duration: '5 hrs', activity: 'Begin sacred trek via Ardhkuwari Cave to Bhawan', place: 'Ardhkuwari Cave', notes: '' },
            { time: '02:00 PM', duration: '2 hrs', activity: 'Mata Vaishno Devi Bhawan Darshan & Bhairavnath Temple', place: 'Bhairavnath Temple', notes: '' },
          ],
        };
      }
      if (dNum === dur) {
        return {
          day_number: dNum,
          title: 'Departure with Divine Blessings',
          activities: [
            { time: '09:00 AM', duration: '1.5 hrs', activity: 'Morning Prasad shopping & hotel checkout in Katra', notes: '' },
          ],
        };
      }
      return {
        day_number: dNum,
        title: `Day ${dNum} Recovery & Regional Pilgrimage`,
        activities: [
          { time: '10:00 AM', duration: '2.5 hrs', activity: 'Excursion to Baba Dhansar sacred waterfall', place: 'Baba Dhansar', notes: '' },
        ],
      };
    });

    setLoading(true);
    setError(null);
    try {
      const res = await upsertItinerary({
        title: createTitle.trim() || 'Sacred Vaishno Devi Yatra',
        itinerary: {
          title: createTitle.trim() || 'Sacred Vaishno Devi Yatra',
          destination: 'Shri Mata Vaishno Devi Shrine',
          start_date: createStartDate || undefined,
          duration_days: dur,
          travellers_count: Math.max(1, Number(createPax) || 2),
          days,
        },
      });
      setShowCreateModal(false);
      await loadList();
      if (res?.itinerary?.itinerary_id) {
        setSelectedId(res.itinerary.itinerary_id);
        setSelectedDetail(res.itinerary);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create itinerary.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setLoading(true);
    setError(null);
    try {
      await deleteItineraryById(deleteTarget.itinerary_id);
      if (selectedId === deleteTarget.itinerary_id) {
        setSelectedId(null);
        setSelectedDetail(null);
      }
      setDeleteTarget(null);
      await loadList();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to delete itinerary.');
      setDeleteTarget(null);
    } finally {
      setLoading(false);
    }
  };

  const buildCurrentEditPayload = () => {
    if (editOp === 'regenerate_day') {
      return { operation: 'regenerate_day', day_number: activeDayNum, instruction: aiInstruction.trim() || undefined };
    }
    if (editOp === 'add_destination') {
      return { operation: 'add_destination', day_number: activeDayNum, place: addPlace, time: addTime, duration: addDuration };
    }
    if (editOp === 'replace_destination') {
      return { operation: 'replace_destination', day_number: activeDayNum, activity_index: Number(targetActIdx) || 0, new_place: replacePlace };
    }
    if (editOp === 'update_timing') {
      return { operation: 'update_timing', day_number: activeDayNum, activity_index: Number(targetActIdx) || 0, time: editTime, duration: editDuration };
    }
    if (editOp === 'update_preferences') {
      return { operation: 'update_preferences', day_number: activeDayNum, preferences: { pace: dayPace } };
    }
    if (editOp === 'update_notes') {
      return notesScope === 'trip'
        ? { operation: 'update_notes', notes: notesDraft }
        : { operation: 'update_notes', day_number: activeDayNum, notes: notesDraft };
    }
    if (editOp === 'adjust_duration') {
      return { operation: 'adjust_duration', duration_days: Number(newDurationDays) || 1 };
    }
    if (editOp === 'update_metadata') {
      return {
        operation: 'update_metadata',
        title: metaTitle,
        start_date: metaStartDate || undefined,
        travellers_count: Number(metaPax) || 2,
      };
    }
    return { operation: editOp };
  };

  const triggerPreview = async (explicitPayload = null) => {
    if (!selectedDetail) return;
    const payload = explicitPayload || buildCurrentEditPayload();
    setEditBusy(true);
    setEditError(null);
    setConfirmImpactChecked(false);
    try {
      const res = await previewItineraryEdit(selectedDetail.itinerary_id, payload);
      setPreviewData(res.preview);
      setPendingPayload(payload);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setEditError(typeof detail === 'string' ? detail : detail?.message || 'Unable to compute edit preview.');
    } finally {
      setEditBusy(false);
    }
  };

  const handleApplyPreview = async () => {
    if (!selectedDetail || !pendingPayload) return;
    setEditBusy(true);
    setEditError(null);
    try {
      const applyBody = {
        ...pendingPayload,
        expected_revision: previewData?.expected_revision ?? selectedDetail.revision,
        confirm_impact: Boolean(confirmImpactChecked || !previewData?.requires_confirmation),
      };
      const res = await applyItineraryEdit(selectedDetail.itinerary_id, applyBody);
      setSelectedDetail(res.itinerary);
      setPreviewData(null);
      setPendingPayload(null);
      await loadList();
    } catch (err) {
      if (err?.response?.status === 409) {
        setEditError('Conflict detected: another collaborator updated this itinerary. Please refresh to view the latest revision.');
      } else {
        const detail = err?.response?.data?.detail;
        setEditError(typeof detail === 'string' ? detail : detail?.message || 'Could not apply changes.');
      }
    } finally {
      setEditBusy(false);
    }
  };

  const handleUndo = async () => {
    if (!selectedDetail) return;
    setEditBusy(true);
    setEditError(null);
    try {
      const res = await undoItineraryEdit(selectedDetail.itinerary_id, selectedDetail.revision);
      setSelectedDetail(res.itinerary);
      await loadList();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setEditError(typeof detail === 'string' ? detail : detail?.message || 'Could not revert last edit.');
    } finally {
      setEditBusy(false);
    }
  };

  const openShareModalFor = async (itinId) => {
    setShowShareModal(true);
    setShareBusy(true);
    setLatestInvite(null);
    try {
      const res = await listItineraryShares(itinId);
      setShareData({ members: res.members || [], invites: res.invites || [] });
    } catch (err) {
      setEditError(err?.response?.data?.detail || 'Only the owner can manage sharing.');
      setShowShareModal(false);
    } finally {
      setShareBusy(false);
    }
  };

  const handleGenerateInvite = async () => {
    const targetId = selectedDetail?.itinerary_id;
    if (!targetId) return;
    setShareBusy(true);
    try {
      const res = await createItineraryInvite(targetId, { role: shareRole, expiresInHours: Number(shareExpiryHours) || 72 });
      setLatestInvite(res.share);
      const updated = await listItineraryShares(targetId);
      setShareData({ members: updated.members || [], invites: updated.invites || [] });
    } catch (err) {
      setEditError(err?.response?.data?.detail || 'Failed to generate invitation link.');
    } finally {
      setShareBusy(false);
    }
  };

  const handleChangeMemberRole = async (memberId, newRole) => {
    if (!selectedDetail) return;
    setShareBusy(true);
    try {
      await updateItineraryMemberRole(selectedDetail.itinerary_id, memberId, newRole);
      const updated = await listItineraryShares(selectedDetail.itinerary_id);
      setShareData({ members: updated.members || [], invites: updated.invites || [] });
      await loadDetail(selectedDetail.itinerary_id);
    } finally {
      setShareBusy(false);
    }
  };

  const handleRevokeMember = async (memberId) => {
    if (!selectedDetail) return;
    setShareBusy(true);
    try {
      await revokeItineraryMember(selectedDetail.itinerary_id, memberId);
      const updated = await listItineraryShares(selectedDetail.itinerary_id);
      setShareData({ members: updated.members || [], invites: updated.invites || [] });
      await loadDetail(selectedDetail.itinerary_id);
      await loadList();
    } finally {
      setShareBusy(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    if (!selectedDetail) return;
    setShareBusy(true);
    try {
      await revokeItineraryInvite(selectedDetail.itinerary_id, inviteId);
      const updated = await listItineraryShares(selectedDetail.itinerary_id);
      setShareData({ members: updated.members || [], invites: updated.invites || [] });
    } finally {
      setShareBusy(false);
    }
  };

  const filteredItems = items.filter((item) => {
    const matchesRole =
      roleFilter === 'ALL' ||
      (roleFilter === 'OWNER' && item.my_role === 'OWNER') ||
      (roleFilter === 'SHARED' && item.my_role !== 'OWNER');
    if (!matchesRole) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      String(item.title || '').toLowerCase().includes(q) ||
      String(item.destination || '').toLowerCase().includes(q) ||
      (item.destinations || []).some((d) => String(d).toLowerCase().includes(q))
    );
  });

  // ------------------------------------------------------------------
  // RENDER: Detail & Smart Editor Workspace
  // ------------------------------------------------------------------
  if (selectedId && selectedDetail) {
    const days = selectedDetail.data?.days || [];
    const currentDayObj = days.find((d) => Number(d.day_number) === Number(activeDayNum)) || days[0] || null;
    const canEdit = selectedDetail.can_edit;
    const isOwner = selectedDetail.is_owner;

    return (
      <div data-testid="itinerary-detail-workspace" style={{ maxWidth: '1040px', margin: '0 auto', padding: '1.25rem 1rem 3rem' }}>
        {/* Top Breadcrumb + Action Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '1rem' }}>
          <button
            type="button"
            data-testid="back-to-itineraries-btn"
            onClick={() => {
              setSelectedId(null);
              setSelectedDetail(null);
              setIsEditing(false);
              setPreviewData(null);
              setEditError(null);
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: '#FFFCF9',
              border: '1px solid #E9DED6',
              borderRadius: '10px',
              padding: '0.45rem 0.9rem',
              fontWeight: 700,
              color: '#54152D',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={15} />
            <span>Back to Itineraries</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <RoleBadge role={selectedDetail.my_role} />
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#796D69' }}>
              Rev v{selectedDetail.revision} · {selectedDetail.sharing_status}
            </span>
            {canEdit && (
              <button
                type="button"
                data-testid="toggle-smart-editor-btn"
                onClick={() => setIsEditing((v) => !v)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: isEditing ? '#54152D' : '#FFFCF9',
                  color: isEditing ? '#FFFFFF' : '#54152D',
                  border: '1px solid #54152D',
                  borderRadius: '10px',
                  padding: '0.45rem 0.9rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Edit3 size={14} />
                <span>{isEditing ? 'Close Editor' : 'Smart Edit'}</span>
              </button>
            )}
            {canEdit && selectedDetail.can_undo && (
              <button
                type="button"
                data-testid="undo-itinerary-btn"
                disabled={editBusy}
                onClick={handleUndo}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  background: '#F2EAE4',
                  color: '#54152D',
                  border: '1px solid #E9DED6',
                  borderRadius: '10px',
                  padding: '0.45rem 0.85rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <RotateCcw size={14} />
                <span>Undo</span>
              </button>
            )}
            {isOwner && (
              <button
                type="button"
                data-testid="open-share-modal-btn"
                onClick={() => openShareModalFor(selectedDetail.itinerary_id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  background: '#FFFCF9',
                  color: '#54152D',
                  border: '1px solid #E9DED6',
                  borderRadius: '10px',
                  padding: '0.45rem 0.85rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Share2 size={14} />
                <span>Share</span>
              </button>
            )}
            {onProceedToBooking && (
              <button
                type="button"
                onClick={() => onProceedToBooking(selectedDetail.data)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: '#54152D',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '0.48rem 0.95rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Ticket size={14} />
                <span>Book Yatra</span>
              </button>
            )}
          </div>
        </div>

        {/* Summary Card */}
        <div
          style={{
            background: '#FFFCF9',
            border: '1.5px solid #E9DED6',
            borderRadius: '16px',
            padding: '1.25rem',
            marginBottom: '1rem',
          }}
        >
          <h2 style={{ margin: '0 0 0.5rem', color: '#54152D', fontFamily: 'var(--font-serif, Cinzel, serif)', fontSize: '1.35rem' }}>
            {selectedDetail.title}
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '0.84rem', color: '#5D4B4F', fontWeight: 600 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <CalendarDays size={14} /> {selectedDetail.start_date || 'Flexible Dates'} {selectedDetail.end_date ? `→ ${selectedDetail.end_date}` : ''} ({selectedDetail.duration_days} Days)
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <Users size={14} /> {selectedDetail.travellers_count} Travellers
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <Clock size={14} /> Updated {new Date(selectedDetail.updated_at).toLocaleDateString()}
            </span>
          </div>
          {selectedDetail.data?.notes ? (
            <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.8rem', background: '#F2EAE4', borderRadius: '10px', fontSize: '0.84rem', color: '#30272A' }}>
              <strong>Trip Notes:</strong> {selectedDetail.data.notes}
            </div>
          ) : null}
        </div>

        {editError && (
          <div
            data-testid="itinerary-edit-error"
            style={{
              background: '#FEE2E2',
              border: '1px solid #FCA5A5',
              color: '#991B1B',
              padding: '0.75rem 1rem',
              borderRadius: '12px',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            <span>{editError}</span>
            <button
              type="button"
              onClick={() => loadDetail(selectedDetail.itinerary_id)}
              style={{ background: '#991B1B', color: '#FFF', border: 'none', borderRadius: '8px', padding: '4px 10px', cursor: 'pointer', fontWeight: 700 }}
            >
              Refresh Latest
            </button>
          </div>
        )}

        {/* Smart Partial Editor Panel (OWNER / EDITOR only) */}
        {isEditing && canEdit && (
          <div
            data-testid="smart-partial-editor-panel"
            style={{
              background: '#FAF5F0',
              border: '1.5px solid #D9C3B4',
              borderRadius: '16px',
              padding: '1.1rem',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '0.75rem' }}>
              <div style={{ fontWeight: 800, color: '#54152D', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={16} />
                <span>Smart Partial Editor (Selected Day / Field Only — Other Days Preserved)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#54152D' }}>Target Day:</label>
                <select
                  data-testid="editor-day-select"
                  value={activeDayNum}
                  onChange={(e) => {
                    setActiveDayNum(Number(e.target.value));
                    setTargetActIdx(0);
                  }}
                  style={{ padding: '4px 10px', borderRadius: '8px', border: '1px solid #E9DED6', fontWeight: 700 }}
                >
                  {days.map((d) => (
                    <option key={d.day_number} value={d.day_number}>
                      Day {d.day_number}: {d.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Operation Selector Pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '0.9rem' }}>
              {[
                { key: 'regenerate_day', label: 'Regenerate Day' },
                { key: 'add_destination', label: 'Add Destination' },
                { key: 'replace_destination', label: 'Replace Place' },
                { key: 'update_timing', label: 'Timings & Duration' },
                { key: 'update_preferences', label: 'Day Preferences' },
                { key: 'update_notes', label: 'Notes' },
                { key: 'adjust_duration', label: 'Adjust Trip Days' },
                { key: 'update_metadata', label: 'Trip Details' },
              ].map((op) => (
                <button
                  key={op.key}
                  type="button"
                  data-testid={`editor-op-${op.key}`}
                  onClick={() => setEditOp(op.key)}
                  style={{
                    padding: '5px 11px',
                    borderRadius: '999px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    border: editOp === op.key ? '1px solid #54152D' : '1px solid #E9DED6',
                    background: editOp === op.key ? '#54152D' : '#FFFCF9',
                    color: editOp === op.key ? '#FFFFFF' : '#54152D',
                  }}
                >
                  {op.label}
                </button>
              ))}
            </div>

            {/* Operation Form Controls */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {editOp === 'regenerate_day' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, marginBottom: '4px', color: '#54152D' }}>
                    Describe change for Day {activeDayNum} only (e.g., "Make it relaxed with Baba Dhansar"):
                  </label>
                  <input
                    type="text"
                    data-testid="editor-ai-instruction"
                    value={aiInstruction}
                    onChange={(e) => setAiInstruction(e.target.value)}
                    placeholder="e.g., Add serene evening Aarti & keep pace relaxed..."
                    style={{ width: '100%', padding: '0.55rem 0.75rem', borderRadius: '10px', border: '1px solid #E9DED6', boxSizing: 'border-box' }}
                  />
                </div>
              )}

              {editOp === 'add_destination' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>Destination</label>
                    <select value={addPlace} onChange={(e) => setAddPlace(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }}>
                      {PLACE_SUGGESTIONS.map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>Start Time</label>
                    <input value={addTime} onChange={(e) => setAddTime(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>Duration</label>
                    <input value={addDuration} onChange={(e) => setAddDuration(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
                  </div>
                </div>
              )}

              {(editOp === 'replace_destination' || editOp === 'update_timing') && currentDayObj && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>Target Activity</label>
                    <select value={targetActIdx} onChange={(e) => setTargetActIdx(Number(e.target.value))} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }}>
                      {(currentDayObj.activities || []).map((a, idx) => (
                        <option key={idx} value={idx}>#{idx + 1}: {formatActLine(a).activity}</option>
                      ))}
                    </select>
                  </div>
                  {editOp === 'replace_destination' ? (
                    <div>
                      <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>New Destination</label>
                      <select value={replacePlace} onChange={(e) => setReplacePlace(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }}>
                        {PLACE_SUGGESTIONS.map((p) => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <>
                      <div>
                        <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>New Time</label>
                        <input value={editTime} onChange={(e) => setEditTime(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.76rem', fontWeight: 700 }}>Visit Duration</label>
                        <input value={editDuration} onChange={(e) => setEditDuration(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
                      </div>
                    </>
                  )}
                </div>
              )}

              {editOp === 'update_preferences' && (
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Day {activeDayNum} Pacing:</label>
                  <select value={dayPace} onChange={(e) => setDayPace(e.target.value)} style={{ padding: '0.45rem 0.75rem', borderRadius: '8px', border: '1px solid #E9DED6' }}>
                    <option value="relaxed">Relaxed (Elder-Friendly / Rest Buffers)</option>
                    <option value="moderate">Moderate (Balanced Darshan & Sightseeing)</option>
                    <option value="focused">Focused (Early Morning Shrine Priority)</option>
                  </select>
                </div>
              )}

              {editOp === 'update_notes' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button type="button" onClick={() => setNotesScope('day')} style={{ padding: '3px 10px', borderRadius: '8px', border: '1px solid #E9DED6', background: notesScope === 'day' ? '#54152D' : '#FFF', color: notesScope === 'day' ? '#FFF' : '#54152D', fontWeight: 700 }}>Day {activeDayNum} Note</button>
                    <button type="button" onClick={() => setNotesScope('trip')} style={{ padding: '3px 10px', borderRadius: '8px', border: '1px solid #E9DED6', background: notesScope === 'trip' ? '#54152D' : '#FFF', color: notesScope === 'trip' ? '#FFF' : '#54152D', fontWeight: 700 }}>Trip-Wide Note</button>
                  </div>
                  <textarea
                    rows={2}
                    value={notesDraft}
                    onChange={(e) => setNotesDraft(e.target.value)}
                    placeholder="Add special reminders (ponies, locker timing, elderly assistance, etc.)"
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }}
                  />
                </div>
              )}

              {editOp === 'adjust_duration' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Total Trip Days (1–90):</label>
                  <input
                    type="number"
                    min={1}
                    max={90}
                    value={newDurationDays}
                    onChange={(e) => setNewDurationDays(e.target.value)}
                    style={{ width: '90px', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }}
                  />
                </div>
              )}

              {editOp === 'update_metadata' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '8px' }}>
                  <input value={metaTitle} onChange={(e) => setMetaTitle(e.target.value)} placeholder="Itinerary Title" style={{ padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }} />
                  <input type="date" value={metaStartDate} onChange={(e) => setMetaStartDate(e.target.value)} style={{ padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }} />
                  <input type="number" min={1} value={metaPax} onChange={(e) => setMetaPax(e.target.value)} placeholder="Travellers" style={{ padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }} />
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  data-testid="preview-edit-btn"
                  disabled={editBusy}
                  onClick={() => triggerPreview()}
                  style={{
                    background: '#54152D',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '0.55rem 1.1rem',
                    fontWeight: 800,
                    cursor: 'pointer',
                  }}
                >
                  {editBusy ? 'Computing Preview...' : 'Preview Before & After'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Day-by-Day Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {days.map((day) => {
            const dNum = day.day_number;
            const acts = day.activities || [];
            return (
              <div
                key={dNum}
                data-testid={`itinerary-day-card-${dNum}`}
                style={{
                  background: '#FFFCF9',
                  border: '1.2px solid #E9DED6',
                  borderRadius: '14px',
                  padding: '1rem 1.15rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '0.6rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ background: '#54152D', color: '#FFF', padding: '2px 9px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 800 }}>
                      Day {dNum}
                    </span>
                    <span style={{ fontWeight: 800, color: '#54152D', fontSize: '0.96rem' }}>{day.title}</span>
                  </div>
                  {day.preferences?.pace && (
                    <span style={{ fontSize: '0.74rem', fontWeight: 700, padding: '2px 8px', borderRadius: '999px', background: '#F2EAE4', color: '#54152D' }}>
                      Pace: {day.preferences.pace}
                    </span>
                  )}
                </div>

                {acts.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {acts.map((act, idx) => {
                      const fmt = formatActLine(act);
                      return (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '8px',
                            background: '#FAF7F5',
                            padding: '0.5rem 0.75rem',
                            borderRadius: '10px',
                            border: '1px solid #EFE5DD',
                          }}
                        >
                          <div style={{ fontSize: '0.85rem', color: '#30272A' }}>
                            {fmt.time && <strong style={{ color: '#A3826C', marginRight: '6px' }}>{fmt.time}</strong>}
                            <span>{fmt.activity}</span>
                            {fmt.duration && <span style={{ color: '#796D69', fontSize: '0.76rem', marginLeft: '6px' }}>({fmt.duration})</span>}
                            {fmt.notes && <div style={{ fontSize: '0.76rem', color: '#6E5A5E', marginTop: '2px' }}>Note: {fmt.notes}</div>}
                          </div>
                          {canEdit && (
                            <button
                              type="button"
                              title="Remove activity (opens preview)"
                              onClick={() => triggerPreview({ operation: 'remove_destination', day_number: dNum, activity_index: idx })}
                              style={{ background: 'transparent', border: 'none', color: '#991B1B', cursor: 'pointer', padding: '4px' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.82rem', color: '#796D69' }}>No scheduled activities on this day yet.</div>
                )}

                {day.notes ? (
                  <div style={{ marginTop: '0.6rem', fontSize: '0.8rem', color: '#5D4B4F', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <FileText size={13} />
                    <span>{day.notes}</span>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>

        {/* Before & After Preview Modal */}
        {previewData && (
          <div
            data-testid="before-after-preview-modal"
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(42, 10, 24, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1rem',
              zIndex: 300,
            }}
          >
            <div style={{ background: '#FFFCF9', borderRadius: '18px', maxWidth: '720px', width: '100%', maxHeight: '85vh', overflowY: 'auto', padding: '1.35rem', border: '1.5px solid #E9DED6' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                <h3 style={{ margin: 0, color: '#54152D' }}>Review Changes (Before &amp; After)</h3>
                <button type="button" onClick={() => setPreviewData(null)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}><X size={18} /></button>
              </div>

              <div style={{ background: '#F2EAE4', padding: '0.75rem', borderRadius: '10px', marginBottom: '0.9rem' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#54152D', marginBottom: '4px' }}>CHANGE SUMMARY</div>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.84rem', color: '#30272A' }}>
                  {(previewData.diff_summary || []).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>

              {previewData.impact_warning && (
                <div style={{ background: '#FEF3C7', border: '1px solid #F59E0B', padding: '0.75rem', borderRadius: '10px', marginBottom: '0.9rem', fontSize: '0.83rem', color: '#92400E' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800, marginBottom: '4px' }}>
                    <AlertTriangle size={15} /> Impact Confirmation Required
                  </div>
                  <p style={{ margin: '0 0 8px' }}>{previewData.impact_warning}</p>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, cursor: 'pointer' }}>
                    <input type="checkbox" checked={confirmImpactChecked} onChange={(e) => setConfirmImpactChecked(e.target.checked)} />
                    <span>I confirm removing those day(s) cleanly</span>
                  </label>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px', marginBottom: '1rem' }}>
                <div style={{ border: '1px solid #E9DED6', borderRadius: '12px', padding: '0.75rem', background: '#FAF7F5' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#796D69', marginBottom: '6px' }}>BEFORE</div>
                  {(previewData.before?.days || [])
                    .filter((d) => !(previewData.affected_days || []).length || previewData.affected_days.includes(d.day_number))
                    .map((d) => (
                      <div key={d.day_number} style={{ marginBottom: '6px', fontSize: '0.8rem' }}>
                        <strong>Day {d.day_number}: {d.title}</strong>
                        <ul style={{ margin: '2px 0 0', paddingLeft: '1rem' }}>
                          {(d.activities || []).map((a, idx) => <li key={idx}>{formatActLine(a).activity}</li>)}
                        </ul>
                      </div>
                    ))}
                </div>
                <div style={{ border: '1.5px solid #54152D', borderRadius: '12px', padding: '0.75rem', background: '#FFFCF9' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#54152D', marginBottom: '6px' }}>AFTER</div>
                  {(previewData.after?.days || [])
                    .filter((d) => !(previewData.affected_days || []).length || previewData.affected_days.includes(d.day_number))
                    .map((d) => (
                      <div key={d.day_number} style={{ marginBottom: '6px', fontSize: '0.8rem' }}>
                        <strong>Day {d.day_number}: {d.title}</strong>
                        <ul style={{ margin: '2px 0 0', paddingLeft: '1rem' }}>
                          {(d.activities || []).map((a, idx) => <li key={idx}>{formatActLine(a).activity}</li>)}
                        </ul>
                      </div>
                    ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  type="button"
                  data-testid="cancel-preview-btn"
                  onClick={() => setPreviewData(null)}
                  style={{ padding: '0.5rem 1rem', borderRadius: '10px', border: '1px solid #E9DED6', background: '#FFF', fontWeight: 700, cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  data-testid="apply-preview-btn"
                  disabled={editBusy || (previewData.requires_confirmation && !confirmImpactChecked)}
                  onClick={handleApplyPreview}
                  style={{
                    padding: '0.5rem 1.15rem',
                    borderRadius: '10px',
                    border: 'none',
                    background: '#54152D',
                    color: '#FFF',
                    fontWeight: 800,
                    cursor: 'pointer',
                    opacity: previewData.requires_confirmation && !confirmImpactChecked ? 0.55 : 1,
                  }}
                >
                  <Check size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                  {editBusy ? 'Applying...' : 'Apply Changes'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Group Collaboration & Sharing Modal (OWNER ONLY) */}
        {showShareModal && (
          <div
            data-testid="share-collaboration-modal"
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(42, 10, 24, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1rem',
              zIndex: 310,
            }}
          >
            <div style={{ background: '#FFFCF9', borderRadius: '18px', maxWidth: '600px', width: '100%', maxHeight: '85vh', overflowY: 'auto', padding: '1.35rem', border: '1.5px solid #E9DED6' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.9rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#54152D', fontWeight: 800, fontSize: '1.05rem' }}>
                  <Shield size={18} /> Group Trip Collaboration &amp; Access
                </div>
                <button type="button" onClick={() => setShowShareModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}><X size={18} /></button>
              </div>

              <div style={{ background: '#F2EAE4', borderRadius: '12px', padding: '0.85rem', marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#54152D', marginBottom: '8px' }}>CREATE SECURE INVITE LINK</div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <select data-testid="share-role-select" value={shareRole} onChange={(e) => setShareRole(e.target.value)} style={{ padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', fontWeight: 700 }}>
                    <option value="VIEWER">Viewer (Read-Only)</option>
                    <option value="EDITOR">Editor (Can Edit Days)</option>
                  </select>
                  <select value={shareExpiryHours} onChange={(e) => setShareExpiryHours(e.target.value)} style={{ padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6' }}>
                    <option value={24}>Expires in 24 hrs</option>
                    <option value={72}>Expires in 3 days</option>
                    <option value={168}>Expires in 7 days</option>
                  </select>
                  <button
                    type="button"
                    data-testid="generate-invite-btn"
                    disabled={shareBusy}
                    onClick={handleGenerateInvite}
                    style={{ background: '#54152D', color: '#FFF', border: 'none', borderRadius: '8px', padding: '0.48rem 0.9rem', fontWeight: 800, cursor: 'pointer' }}
                  >
                    Generate Invite
                  </button>
                </div>

                {latestInvite && (
                  <div data-testid="generated-invite-box" style={{ marginTop: '0.75rem', background: '#FFFCF9', border: '1px solid #E9DED6', borderRadius: '10px', padding: '0.65rem', fontSize: '0.78rem' }}>
                    <div style={{ fontWeight: 700, color: '#065F46', marginBottom: '4px' }}>
                      Invite Ready ({latestInvite.role}) — Expires {new Date(latestInvite.expires_at).toLocaleString()}
                    </div>
                    <div style={{ wordBreak: 'break-all', fontFamily: 'monospace', background: '#FAF7F5', padding: '5px', borderRadius: '6px', marginBottom: '6px' }}>
                      {latestInvite.invite_url}
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard?.writeText(latestInvite.invite_url || latestInvite.invite_token);
                        setCopiedId(latestInvite.invite_id);
                        setTimeout(() => setCopiedId(null), 2000);
                      }}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#54152D', color: '#FFF', border: 'none', borderRadius: '6px', padding: '4px 10px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                    >
                      <Copy size={12} /> {copiedId === latestInvite.invite_id ? 'Copied!' : 'Copy Invite Link'}
                    </button>
                  </div>
                )}
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#54152D', marginBottom: '6px' }}>GROUP MEMBERS ({shareData.members.length})</div>
                {shareData.members.map((m) => (
                  <div key={m.user_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px', borderBottom: '1px solid #EFE5DD', fontSize: '0.82rem' }}>
                    <div>
                      <strong>{m.masked_email}</strong> <RoleBadge role={m.role} />
                    </div>
                    {m.role !== 'OWNER' && (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <select value={m.role} onChange={(e) => handleChangeMemberRole(m.user_id, e.target.value)} style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '6px' }}>
                          <option value="VIEWER">VIEWER</option>
                          <option value="EDITOR">EDITOR</option>
                        </select>
                        <button type="button" onClick={() => handleRevokeMember(m.user_id)} style={{ fontSize: '0.74rem', background: '#FEE2E2', color: '#991B1B', border: 'none', borderRadius: '6px', padding: '3px 8px', fontWeight: 700, cursor: 'pointer' }}>
                          Revoke
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#54152D', marginBottom: '6px' }}>INVITATION LINKS ({shareData.invites.length})</div>
                {shareData.invites.map((inv) => (
                  <div key={inv.invite_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px', borderBottom: '1px solid #EFE5DD', fontSize: '0.78rem' }}>
                    <span>{inv.role} · {inv.status} · Used {inv.use_count}x</span>
                    {inv.status === 'ACTIVE' && (
                      <button type="button" onClick={() => handleRevokeInvite(inv.invite_id)} style={{ fontSize: '0.74rem', background: '#FEE2E2', color: '#991B1B', border: 'none', borderRadius: '6px', padding: '3px 8px', fontWeight: 700, cursor: 'pointer' }}>
                        Revoke Link
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ------------------------------------------------------------------
  // RENDER: Main Itineraries List Screen
  // ------------------------------------------------------------------
  return (
    <div data-testid="itineraries-section-view" style={{ maxWidth: '1080px', margin: '0 auto', padding: '1.25rem 1rem 3rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontFamily: 'var(--font-serif, Cinzel, serif)', fontSize: '1.5rem', color: '#54152D', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Map size={22} /> <span>My Itineraries</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.86rem', color: '#796D69' }}>
            Manage your saved pilgrimage schedules, edit individual days, and collaborate securely with travel companions.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {user && (
            <>
              <button
                type="button"
                data-testid="refresh-itineraries-btn"
                onClick={loadList}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '0.5rem 0.9rem', borderRadius: '10px', border: '1px solid #E9DED6', background: '#FFFCF9', color: '#54152D', fontWeight: 700, cursor: 'pointer' }}
              >
                <RefreshCw size={14} /> Refresh
              </button>
              <button
                type="button"
                data-testid="create-itinerary-btn"
                onClick={() => setShowCreateModal(true)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '0.5rem 1rem', borderRadius: '10px', border: 'none', background: '#54152D', color: '#FFFFFF', fontWeight: 800, cursor: 'pointer' }}
              >
                <Plus size={15} /> Create Itinerary
              </button>
            </>
          )}
        </div>
      </div>

      {inviteNotice && (
        <div style={{ background: '#D1FAE5', border: '1px solid #34D399', color: '#065F46', padding: '0.65rem 0.9rem', borderRadius: '10px', marginBottom: '1rem', fontWeight: 700, fontSize: '0.84rem' }}>
          {inviteNotice}
        </div>
      )}

      {error && (
        <div data-testid="itineraries-error-banner" style={{ background: '#FEE2E2', border: '1px solid #FCA5A5', color: '#991B1B', padding: '0.75rem 1rem', borderRadius: '12px', marginBottom: '1rem', fontWeight: 600, fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {!user ? (
        <div data-testid="itineraries-signin-prompt" style={{ background: '#FFFCF9', border: '1.5px solid #E9DED6', borderRadius: '16px', padding: '2rem', textAlign: 'center' }}>
          <Map size={34} color="#54152D" style={{ marginBottom: '8px' }} />
          <h3 style={{ margin: '0 0 6px', color: '#54152D' }}>Sign in to save, edit &amp; share your Itineraries</h3>
          <p style={{ margin: '0 0 1rem', fontSize: '0.88rem', color: '#796D69' }}>
            Guest planning remains open anytime, while signing in syncs saved trips and lets you accept group collaboration invites.
          </p>
          <button
            type="button"
            onClick={onOpenAuthModal}
            style={{ background: '#54152D', color: '#FFF', border: 'none', borderRadius: '10px', padding: '0.6rem 1.3rem', fontWeight: 800, cursor: 'pointer' }}
          >
            Sign In with Email OTP
          </button>
        </div>
      ) : (
        <>
          {/* Search, Filter & Accept Invite Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '1rem', alignItems: 'center' }}>
            <div style={{ flex: '1 1 240px', position: 'relative' }}>
              <Search size={15} color="#796D69" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                data-testid="search-itineraries-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search itineraries or destinations..."
                style={{ width: '100%', padding: '0.5rem 0.75rem 0.5rem 2rem', borderRadius: '10px', border: '1px solid #E9DED6', background: '#FFFCF9', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '4px', background: '#F2EAE4', padding: '3px', borderRadius: '10px' }}>
              {['ALL', 'OWNER', 'SHARED'].map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setRoleFilter(f)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    background: roleFilter === f ? '#54152D' : 'transparent',
                    color: roleFilter === f ? '#FFF' : '#54152D',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {f === 'ALL' ? 'All Trips' : f === 'OWNER' ? 'Owned' : 'Shared with Me'}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '6px', flex: '1 1 230px' }}>
              <input
                type="text"
                data-testid="join-invite-input"
                value={inviteInput}
                onChange={(e) => setInviteInput(e.target.value)}
                placeholder="Paste group invite token or link..."
                style={{ flex: 1, padding: '0.48rem 0.7rem', borderRadius: '10px', border: '1px solid #E9DED6', background: '#FFFCF9', fontSize: '0.82rem' }}
              />
              <button
                type="button"
                data-testid="accept-invite-btn"
                onClick={() => handleAcceptInviteToken(inviteInput)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '0.48rem 0.85rem', borderRadius: '10px', border: '1px solid #54152D', background: '#FFFCF9', color: '#54152D', fontWeight: 700, cursor: 'pointer' }}
              >
                <LinkIcon size={13} /> Join
              </button>
            </div>
          </div>

          {loading ? (
            <div data-testid="itineraries-loading" style={{ textAlign: 'center', padding: '2.5rem', color: '#796D69', fontWeight: 600 }}>
              Loading saved itineraries...
            </div>
          ) : filteredItems.length === 0 ? (
            <div data-testid="itineraries-empty-state" style={{ background: '#FFFCF9', border: '1.5px dashed #D9C3B4', borderRadius: '16px', padding: '2.25rem', textAlign: 'center' }}>
              <CalendarDays size={32} color="#54152D" style={{ marginBottom: '8px' }} />
              <h3 style={{ margin: '0 0 6px', color: '#54152D' }}>No saved itineraries yet</h3>
              <p style={{ margin: '0 0 1rem', fontSize: '0.86rem', color: '#796D69' }}>
                Create a structured trip here or ask the Yatra AI Assistant to plan your pilgrimage.
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  data-testid="empty-create-itinerary-btn"
                  onClick={() => setShowCreateModal(true)}
                  style={{ background: '#54152D', color: '#FFF', border: 'none', borderRadius: '10px', padding: '0.55rem 1.15rem', fontWeight: 800, cursor: 'pointer' }}
                >
                  Create Itinerary
                </button>
                {onReturnToAssistant && (
                  <button
                    type="button"
                    onClick={onReturnToAssistant}
                    style={{ background: '#F2EAE4', color: '#54152D', border: '1px solid #E9DED6', borderRadius: '10px', padding: '0.55rem 1.15rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Ask AI Assistant
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '14px' }}>
              {filteredItems.map((item) => (
                <div
                  key={item.itinerary_id}
                  data-testid={`itinerary-card-${item.itinerary_id}`}
                  style={{
                    background: '#FFFCF9',
                    border: '1.5px solid #E9DED6',
                    borderRadius: '16px',
                    padding: '1rem 1.1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px',
                    boxShadow: '0 2px 8px rgba(84, 21, 45, 0.04)',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                      <RoleBadge role={item.my_role} />
                      <span style={{ fontSize: '0.73rem', fontWeight: 700, color: '#796D69' }}>{item.sharing_status}</span>
                    </div>
                    <h3 style={{ margin: '0 0 6px', fontSize: '1.05rem', color: '#54152D' }}>{item.title}</h3>
                    <div style={{ fontSize: '0.8rem', color: '#5D4B4F', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span><strong>Destinations:</strong> {(item.destinations || []).slice(0, 3).join(', ') || item.destination}</span>
                      <span>
                        <strong>Dates:</strong> {item.start_date || 'Flexible'} {item.end_date ? `→ ${item.end_date}` : ''}
                      </span>
                      <span>
                        <strong>Schedule:</strong> {item.duration_days} Days · {item.travellers_count} Travellers
                      </span>
                      <span style={{ color: '#796D69', fontSize: '0.74rem' }}>
                        Updated {new Date(item.updated_at).toLocaleDateString()} · v{item.revision}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', paddingTop: '6px', borderTop: '1px solid #EFE5DD' }}>
                    <button
                      type="button"
                      data-testid={`view-itinerary-btn-${item.itinerary_id}`}
                      onClick={() => {
                        setSelectedId(item.itinerary_id);
                        setIsEditing(false);
                        loadDetail(item.itinerary_id);
                      }}
                      style={{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '4px', padding: '0.42rem 0.65rem', borderRadius: '8px', background: '#54152D', color: '#FFF', border: 'none', fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer' }}
                    >
                      <Eye size={13} /> View
                    </button>

                    {item.can_edit && (
                      <button
                        type="button"
                        data-testid={`edit-itinerary-btn-${item.itinerary_id}`}
                        onClick={() => {
                          setSelectedId(item.itinerary_id);
                          setIsEditing(true);
                          loadDetail(item.itinerary_id);
                        }}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '0.42rem 0.65rem', borderRadius: '8px', background: '#F2EAE4', color: '#54152D', border: '1px solid #E9DED6', fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer' }}
                      >
                        <Edit3 size={13} /> Edit
                      </button>
                    )}

                    {item.can_manage_shares && (
                      <button
                        type="button"
                        data-testid={`share-itinerary-btn-${item.itinerary_id}`}
                        onClick={async () => {
                          setSelectedId(item.itinerary_id);
                          await loadDetail(item.itinerary_id);
                          openShareModalFor(item.itinerary_id);
                        }}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '0.42rem 0.65rem', borderRadius: '8px', background: '#FFFCF9', color: '#54152D', border: '1px solid #E9DED6', fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer' }}
                      >
                        <Share2 size={13} /> Share
                      </button>
                    )}

                    {item.can_delete && (
                      <button
                        type="button"
                        data-testid={`delete-itinerary-btn-${item.itinerary_id}`}
                        onClick={() => setDeleteTarget(item)}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '0.42rem 0.6rem', borderRadius: '8px', background: '#FEE2E2', color: '#991B1B', border: 'none', fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer' }}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div
          data-testid="delete-itinerary-confirm-modal"
          style={{ position: 'fixed', inset: 0, background: 'rgba(42, 10, 24, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', zIndex: 320 }}
        >
          <div style={{ background: '#FFFCF9', borderRadius: '16px', padding: '1.25rem', maxWidth: '400px', width: '100%', border: '1.5px solid #E9DED6' }}>
            <h3 style={{ margin: '0 0 6px', color: '#991B1B' }}>Delete Itinerary?</h3>
            <p style={{ margin: '0 0 1rem', fontSize: '0.86rem', color: '#5D4B4F' }}>
              Are you sure you want to permanently delete <strong>{deleteTarget.title}</strong>? Shared collaborator access will also be removed.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" onClick={() => setDeleteTarget(null)} style={{ padding: '0.45rem 0.9rem', borderRadius: '8px', border: '1px solid #E9DED6', background: '#FFF', fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
              <button type="button" data-testid="confirm-delete-itinerary-btn" onClick={handleConfirmDelete} style={{ padding: '0.45rem 0.9rem', borderRadius: '8px', border: 'none', background: '#991B1B', color: '#FFF', fontWeight: 800, cursor: 'pointer' }}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Itinerary Modal */}
      {showCreateModal && (
        <div
          data-testid="create-itinerary-modal"
          style={{ position: 'fixed', inset: 0, background: 'rgba(42, 10, 24, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', zIndex: 320 }}
        >
          <form onSubmit={handleCreateItinerary} style={{ background: '#FFFCF9', borderRadius: '16px', padding: '1.25rem', maxWidth: '440px', width: '100%', border: '1.5px solid #E9DED6', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h3 style={{ margin: 0, color: '#54152D' }}>Create New Pilgrimage Itinerary</h3>
            <input required value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} placeholder="Trip Title" style={{ padding: '0.5rem', borderRadius: '8px', border: '1px solid #E9DED6' }} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 700 }}>Days</label>
                <input type="number" min={1} max={90} value={createDays} onChange={(e) => setCreateDays(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 700 }}>Travellers</label>
                <input type="number" min={1} value={createPax} onChange={(e) => setCreatePax(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
              </div>
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 700 }}>Start Date (optional)</label>
              <input type="date" value={createStartDate} onChange={(e) => setCreateStartDate(e.target.value)} style={{ width: '100%', padding: '0.45rem', borderRadius: '8px', border: '1px solid #E9DED6', boxSizing: 'border-box' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
              <button type="button" onClick={() => setShowCreateModal(false)} style={{ padding: '0.45rem 0.9rem', borderRadius: '8px', border: '1px solid #E9DED6', background: '#FFF', fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
              <button type="submit" data-testid="submit-create-itinerary-btn" style={{ padding: '0.45rem 1rem', borderRadius: '8px', border: 'none', background: '#54152D', color: '#FFF', fontWeight: 800, cursor: 'pointer' }}>Save Itinerary</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

