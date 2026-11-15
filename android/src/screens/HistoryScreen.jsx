import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import { MessageSquareIcon, ClockIcon, PlusIcon } from '../components/Icons';
import { fetchChatHistory } from '../services/api';
import { getLocalChatMessages } from '../utils/storage';

export default function HistoryScreen({ navigation }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchChatHistory();
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data?.conversations && Array.isArray(data.conversations)) {
        items = data.conversations;
      } else if (data?.history && Array.isArray(data.history)) {
        items = data.history;
      }

      // If no cloud history found, check for local guest session
      if (items.length === 0) {
        const local = await getLocalChatMessages();
        if (local && local.length > 1) {
          const firstUser = local.find((m) => m.role === 'user');
          items = [
            {
              conversation_id: 'guest-local-session',
              title: firstUser?.content ? (firstUser.content.slice(0, 45) + (firstUser.content.length > 45 ? '...' : '')) : 'Guest Consultation',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              messages: local,
              preview: firstUser?.content || 'Recent guest pilgrimage discussion.',
            },
          ];
        }
      }
      setHistory(items);
    } catch (e) {
      // Fallback if backend is offline and no network response
      const local = await getLocalChatMessages();
      if (local && local.length > 1) {
        const firstUser = local.find((m) => m.role === 'user');
        setHistory([
          {
            conversation_id: 'guest-local-session',
            title: firstUser?.content ? (firstUser.content.slice(0, 45) + (firstUser.content.length > 45 ? '...' : '')) : 'Guest Consultation',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            messages: local,
            preview: firstUser?.content || 'Recent guest pilgrimage discussion.',
          },
        ]);
      } else {
        setHistory([]);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadHistory();
  };

  const handleStartNewChat = () => {
    navigation.navigate('Assistant', { sessionId: null, messages: null, loadedAt: Date.now() });
  };

  const renderItem = ({ item }) => {
    const convId = item.conversation_id || item.session_id;
    const msgCount = item.message_count || (Array.isArray(item.messages) ? item.messages.length : 0);
    const dateVal = item.updated_at || item.created_at;
    const dateStr = dateVal ? new Date(dateVal).toLocaleDateString() : 'Recent';

    return (
      <TouchableOpacity
        style={styles.historyCard}
        onPress={() => {
          Alert.alert(
            'Resume Conversation',
            `Load conversation: "${item.title || convId}"?`,
            [
              { text: 'Cancel', style: 'cancel' },
              {
                text: 'Open',
                onPress: () =>
                  navigation.navigate('Assistant', {
                    sessionId: convId,
                    messages: item.messages,
                    tripRequest: item.trip_request,
                    loadedAt: Date.now(),
                  }),
              },
            ]
          );
        }}
        activeOpacity={0.7}
      >
        <View style={styles.cardHeader}>
          <MessageSquareIcon size={16} color={colors.primary} />
          <Text style={styles.cardTitle} numberOfLines={1}>
            {item.title || `Pilgrimage Session (${convId?.slice(0, 8)})`}
          </Text>
        </View>
        <Text style={styles.cardPreview} numberOfLines={2}>
          {item.preview || 'Discussion on Vaishno Devi Yatra planning, routes, and timings.'}
        </Text>
        <View style={styles.cardFooter}>
          <Text style={styles.cardDate}>{dateStr}</Text>
          <Text style={styles.cardBadge}>
            {msgCount ? `${msgCount} messages` : 'Archived'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <Header
        title="Yatra History"
        subtitle="Saved Consultations"
        showBack={true}
        onBackPress={() => navigation.goBack()}
      />

      <View style={styles.actionBanner}>
        <TouchableOpacity style={styles.newChatBtn} onPress={handleStartNewChat}>
          <PlusIcon size={14} color={colors.surface} />
          <Text style={[styles.newChatBtnText, { marginLeft: 6 }]}>Start Fresh Yatra Consultation</Text>
        </TouchableOpacity>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Retrieving pilgrimage records...</Text>
        </View>
      ) : history.length === 0 ? (
        <View style={styles.centerContainer}>
          <ClockIcon size={44} color={colors.textMuted} />
          <Text style={[styles.emptyTitle, { marginTop: 12 }]}>No Previous Conversations</Text>
          <Text style={styles.emptySubtitle}>
            Your conversations with Yatra AI will appear here for future reference.
          </Text>
        </View>
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item, idx) => item.session_id || String(idx)}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              colors={[colors.primary]}
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  actionBanner: {
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  newChatBtn: {
    flexDirection: 'row',
    backgroundColor: colors.primary,
    paddingVertical: 10,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  newChatBtnText: {
    color: colors.surface,
    fontSize: 13,
    fontWeight: '700',
  },
  listContent: {
    padding: spacing.md,
    gap: spacing.sm,
  },
  historyCard: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusMd,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderLight,
    ...spacing.shadowSm,
    marginBottom: spacing.xs,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardIcon: {
    fontSize: 16,
    marginRight: spacing.xs,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.primary,
    flex: 1,
    marginLeft: 6,
  },
  cardPreview: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 16,
    marginBottom: spacing.xs,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  cardDate: {
    fontSize: 11,
    color: colors.textLight,
  },
  cardBadge: {
    fontSize: 10,
    color: colors.primary,
    backgroundColor: colors.surfaceSecondary,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    fontWeight: '600',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  loadingText: {
    marginTop: spacing.sm,
    fontSize: 13,
    color: colors.textSecondary,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
    marginBottom: 4,
  },
  emptySubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 16,
  },
});
