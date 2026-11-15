import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors } from '../theme/colors';
import { CheckIcon, AlertCircleIcon } from './Icons';

export default function StatusBanner({ isConnected, backendUrl, latency, onConfigure, onPress }) {
  const handleAction = onConfigure || onPress;

  if (isConnected) {
    return (
      <View style={[styles.container, styles.connectedContainer]}>
        <TouchableOpacity
          style={styles.textRow}
          onPress={handleAction}
          disabled={!handleAction}
          activeOpacity={0.7}
        >
          <View style={styles.dotIndicator} />
          <Text style={styles.connectedText} numberOfLines={1}>
            Connected: <Text style={styles.codeText}>{backendUrl}</Text>
            {latency ? ` (${latency}ms)` : ''}
          </Text>
        </TouchableOpacity>
        {handleAction && (
          <TouchableOpacity onPress={handleAction} style={styles.changeBtn}>
            <Text style={styles.changeBtnText}>Change</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  }

  return (
    <View style={[styles.container, styles.disconnectedContainer]}>
      <TouchableOpacity
        style={styles.textRow}
        onPress={handleAction}
        disabled={!handleAction}
        activeOpacity={0.7}
      >
        <AlertCircleIcon size={14} color="#D97706" />
        <Text style={styles.disconnectedText} numberOfLines={2}>
          Backend Disconnected: Live AI planning & booking require an active backend.
        </Text>
      </TouchableOpacity>
      {handleAction && (
        <TouchableOpacity onPress={handleAction} style={styles.connectBtn}>
          <Text style={styles.connectBtnText}>Connect Backend</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
  },
  connectedContainer: {
    backgroundColor: colors.successSubtle,
    borderBottomColor: '#A7F3D0',
  },
  disconnectedContainer: {
    backgroundColor: colors.warningSubtle,
    borderBottomColor: '#FDE68A',
  },
  textRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 8,
  },
  dotIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10B981',
    marginRight: 6,
  },
  connectedText: {
    fontSize: 11,
    color: '#065F46',
    fontWeight: '600',
    flex: 1,
  },
  codeText: {
    fontFamily: 'monospace',
    fontWeight: '700',
  },
  warningIcon: {
    fontSize: 12,
    marginRight: 6,
  },
  disconnectedText: {
    fontSize: 11,
    color: '#92400E',
    fontWeight: '600',
    flex: 1,
  },
  changeBtn: {
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderWidth: 1,
    borderColor: '#059669',
    borderRadius: 4,
  },
  changeBtnText: {
    fontSize: 10,
    color: '#065F46',
    fontWeight: '700',
  },
  connectBtn: {
    backgroundColor: '#B45309',
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 4,
  },
  connectBtnText: {
    fontSize: 10.5,
    color: '#FFFFFF',
    fontWeight: '700',
  },
});
