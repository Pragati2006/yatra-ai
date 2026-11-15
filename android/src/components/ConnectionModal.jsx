import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import { CloseIcon, CheckIcon, AlertCircleIcon, RefreshIcon, InfoIcon } from './Icons';
import {
  getRuntimeApiUrl,
  setRuntimeApiUrl,
  checkBackendHealth,
} from '../services/api';
import {
  validateBackendUrl,
  getPresetUrls,
  isPrivateNetworkHost,
  APPROVED_TUNNEL_HOST_PATTERN,
} from '../utils/urlValidator';

export default function ConnectionModal({ visible, onClose, onConnected }) {
  const [url, setUrl] = useState('');
  const [currentUrl, setCurrentUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    if (visible) {
      loadCurrent();
    }
  }, [visible]);

  const loadCurrent = async () => {
    const cur = await getRuntimeApiUrl();
    setCurrentUrl(cur);
    setUrl(cur);
    setTestResult(null);
    setAcknowledged(false);
  };

  const isPrivateEndpoint = (targetUrl) => {
    try {
      const parsed = new URL(targetUrl);
      return isPrivateNetworkHost(parsed.hostname);
    } catch {
      return (
        targetUrl.includes('10.0.2.2') ||
        targetUrl.includes('localhost') ||
        targetUrl.includes('127.0.0.1')
      );
    }
  };

  const handlePresetSelect = (presetUrl) => {
    setUrl(presetUrl);
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    const validation = validateBackendUrl(url);
    if (!validation.isValid) {
      Alert.alert('Invalid URL', validation.error);
      return;
    }

    setTesting(true);
    setTestResult(null);
    try {
      const result = await checkBackendHealth(url);
      setTestResult(result);
      if (result.ok) {
        Alert.alert('Connection Successful', `Connected to Yatra AI Backend: ${result.data?.status || 'OK'}`);
      } else {
        Alert.alert('Connection Failed', result.error || 'Server unreachable');
      }
    } catch (e) {
      setTestResult({ ok: false, error: e.message });
      Alert.alert('Connection Error', e.message);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    const validation = validateBackendUrl(url);
    if (!validation.isValid) {
      Alert.alert('Invalid URL', validation.error);
      return;
    }

    // Require explicit acknowledgement for remote custom/tunnel URLs (exempts official production Render backend)
    const isLocal = isPrivateEndpoint(url);
    let isOfficialProd = false;
    try {
      const parsedHost = new URL(url).hostname;
      isOfficialProd = (parsedHost || '').toLowerCase() === 'yatra-ai-smap.onrender.com';
    } catch {
      isOfficialProd = false;
    }
    if (!isLocal && !isOfficialProd && !acknowledged) {
      Alert.alert(
        'Security Notice',
        'You are connecting to a remote endpoint. Session tokens will be cleared upon switching backends. Please check the security confirmation checkbox before saving.'
      );
      return;
    }

    const success = await setRuntimeApiUrl(url);
    if (success) {
      Alert.alert('Backend Updated', `Active backend set to: ${url}`);
      if (onConnected) onConnected(url);
      onClose();
    } else {
      Alert.alert('Error', 'Failed to save backend configuration.');
    }
  };

  const presets = getPresetUrls();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.container}>
          <ScrollView showsVerticalScrollIndicator={false}>
            <View style={styles.header}>
              <Text style={styles.title}>Backend Connection</Text>
              <TouchableOpacity onPress={onClose} style={styles.closeBtn} accessibilityLabel="Close">
                <CloseIcon size={16} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={styles.subtitle}>
              Configure your FastAPI backend. Supports local Wi-Fi IP (e.g. 192.168.x.x:8000), Android Emulator (10.0.2.2:8000), or Cloudflare Quick Tunnel.
            </Text>

            <View style={styles.currentBox}>
              <Text style={styles.currentLabel}>Active Backend:</Text>
              <Text style={styles.currentValue} numberOfLines={1}>
                {currentUrl || 'Loading...'}
              </Text>
            </View>

            <Text style={styles.sectionLabel}>Quick Presets</Text>
            <View style={styles.presetsContainer}>
              {presets.map((p, idx) => (
                <TouchableOpacity
                  key={idx}
                  style={[
                    styles.presetChip,
                    url === p.url && styles.presetChipActive,
                  ]}
                  onPress={() => handlePresetSelect(p.url)}
                >
                  <Text
                    style={[
                      styles.presetChipText,
                      url === p.url && styles.presetChipTextActive,
                    ]}
                  >
                    {p.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.sectionLabel}>Backend URL</Text>
            <TextInput
              style={styles.input}
              value={url}
              onChangeText={setUrl}
              placeholder="e.g. http://192.168.1.15:8000 or https://...trycloudflare.com"
              placeholderTextColor={colors.textLight}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />

            {/* Informative banner for Private LAN IPs */}
            {url && isPrivateEndpoint(url) && !url.includes('10.0.2.2') && !url.includes('localhost') && !url.includes('127.0.0.1') && (
              <View style={styles.lanBox}>
                <InfoIcon size={14} color="#1E40AF" style={{ marginTop: 2, marginRight: 6 }} />
                <Text style={styles.lanText}>
                  Private Wi-Fi LAN: Connecting directly to your laptop's IPv4 address. Ensure your phone is on the same Wi-Fi network and laptop firewall allows port 8000.
                </Text>
              </View>
            )}

            {/* Security Notice for remote / tunnel URLs */}
            {url && !isPrivateEndpoint(url) && (
              <View style={styles.securityBox}>
                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                  <AlertCircleIcon size={14} color="#92400E" />
                  <Text style={[styles.securityTitle, { marginLeft: 6, marginBottom: 0 }]}>Security Warning (Phase 12.2.1 Parity)</Text>
                </View>
                <Text style={styles.securityBody}>
                  Connecting to a Cloudflare Quick Tunnel or custom remote server routes your queries and simulated booking requests to that endpoint. Active session tokens are cleared upon switching backends.
                </Text>
                <TouchableOpacity
                  style={styles.checkboxRow}
                  onPress={() => setAcknowledged(!acknowledged)}
                >
                  <View style={[styles.checkbox, acknowledged && styles.checkboxActive]}>
                    {acknowledged && <CheckIcon size={12} color={colors.surface} />}
                  </View>
                  <Text style={styles.checkboxLabel}>
                    I trust this endpoint and authorize communication.
                  </Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Test Connection Button */}
            <TouchableOpacity
              style={[styles.testBtn, testing && styles.btnDisabled]}
              onPress={handleTestConnection}
              disabled={testing}
            >
              {testing ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <RefreshIcon size={14} color={colors.primary} />
                  <Text style={[styles.testBtnText, { marginLeft: 6 }]}>Test Connection</Text>
                </View>
              )}
            </TouchableOpacity>

            {testResult && (
              <View
                style={[
                  styles.resultBox,
                  testResult.ok ? styles.resultSuccess : styles.resultError,
                ]}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  {testResult.ok ? (
                    <CheckIcon size={14} color="#15803D" />
                  ) : (
                    <AlertCircleIcon size={14} color="#B91C1C" />
                  )}
                  <Text
                    style={[
                      styles.resultText,
                      testResult.ok ? styles.resultTextSuccess : styles.resultTextError,
                      { marginLeft: 6 },
                    ]}
                  >
                    {testResult.ok
                      ? `Online (Latency: ${testResult.latencyMs}ms)`
                      : `Unreachable: ${testResult.error}`}
                  </Text>
                </View>
              </View>
            )}

            {/* Save and Cancel Actions */}
            <View style={styles.actionRow}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={onClose}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.saveBtn}
                onPress={handleSave}
              >
                <Text style={styles.saveBtnText}>Save & Apply</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.md,
  },
  container: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusLg,
    padding: spacing.lg,
    width: '100%',
    maxHeight: '90%',
    ...spacing.shadowLg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.primary,
  },
  closeBtn: {
    padding: spacing.xs,
  },
  closeBtnText: {
    fontSize: 18,
    color: colors.textSecondary,
  },
  subtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  currentBox: {
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.sm,
    borderRadius: spacing.radiusSm,
    marginBottom: spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
  },
  currentLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
    textTransform: 'uppercase',
  },
  currentValue: {
    fontSize: 13,
    color: colors.text,
    fontFamily: 'monospace',
    marginTop: 2,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  presetsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginBottom: spacing.md,
  },
  presetChip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: spacing.radiusSm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  presetChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  presetChipText: {
    fontSize: 12,
    color: colors.text,
    fontWeight: '500',
  },
  presetChipTextActive: {
    color: colors.surface,
  },
  input: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: spacing.radiusSm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 14,
    color: colors.text,
    fontFamily: 'monospace',
    marginBottom: spacing.md,
  },
  lanBox: {
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#3B82F6',
    borderRadius: spacing.radiusSm,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  lanText: {
    fontSize: 11,
    color: '#1E40AF',
    lineHeight: 16,
  },
  securityBox: {
    backgroundColor: '#FEF3C7',
    borderWidth: 1,
    borderColor: '#F59E0B',
    borderRadius: spacing.radiusSm,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  securityTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#92400E',
    marginBottom: 4,
  },
  securityBody: {
    fontSize: 11,
    color: '#78350F',
    lineHeight: 16,
    marginBottom: spacing.sm,
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  checkbox: {
    width: 18,
    height: 18,
    borderWidth: 1.5,
    borderColor: '#92400E',
    borderRadius: 3,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.xs,
    backgroundColor: colors.surface,
  },
  checkboxActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  checkIcon: {
    color: colors.surface,
    fontSize: 12,
    fontWeight: 'bold',
  },
  checkboxLabel: {
    fontSize: 11,
    color: '#78350F',
    fontWeight: '500',
    flex: 1,
  },
  testBtn: {
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: spacing.radiusSm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  testBtnText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 13,
  },
  resultBox: {
    padding: spacing.xs,
    borderRadius: spacing.radiusSm,
    marginBottom: spacing.md,
    alignItems: 'center',
  },
  resultSuccess: {
    backgroundColor: '#DEF7EC',
  },
  resultError: {
    backgroundColor: '#FDE8E8',
  },
  resultText: {
    fontSize: 12,
    fontWeight: '500',
  },
  resultTextSuccess: {
    color: '#03543F',
  },
  resultTextError: {
    color: '#9B1C1C',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  cancelBtn: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: spacing.radiusSm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cancelBtnText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '500',
  },
  saveBtn: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: spacing.radiusSm,
  },
  saveBtnText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '600',
  },
});
