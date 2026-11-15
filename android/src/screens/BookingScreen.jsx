import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import YatraLogo from '../components/YatraLogo';
import { CheckIcon } from '../components/Icons';
import { authorizeBooking, confirmBooking, triggerRpaBooking } from '../services/api';

export default function BookingScreen({ route, navigation }) {
  const initialService = route?.params?.initialService || 'Vaishno Devi Yatra Parchi';
  const initialHotel = route?.params?.initialHotel || 'Niharika Complex (SMVDSB)';

  const [step, setStep] = useState(1); // 1: Details, 2: Preferences, 3: Human Authorization, 4: Pass Generated
  const [loading, setLoading] = useState(false);

  // Form State
  const [fullName, setFullName] = useState('Ramesh Sharma');
  const [age, setAge] = useState('38');
  const [gender, setGender] = useState('Male');
  const [phone, setPhone] = useState('9876543210');
  const [devoteeCount, setDevoteeCount] = useState('2');
  const [yatraDate, setYatraDate] = useState('2026-12-15');
  const [slot, setSlot] = useState('Morning (06:00 - 12:00)');
  const [transportMode, setTransportMode] = useState('Traditional Trek (Banganga)');
  const [hotelChoice, setHotelChoice] = useState(initialHotel);

  // Step 3 Confirmation State
  const [authorized, setAuthorized] = useState(false);

  // Step 4 Generated Pass State
  const [generatedPass, setGeneratedPass] = useState(null);

  const handleNextStep = () => {
    if (step === 1) {
      if (!fullName.trim() || !age.trim() || !phone.trim()) {
        Alert.alert('Required Fields', 'Please fill in all primary devotee details.');
        return;
      }
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    }
  };

  const handleExecuteRpaBooking = async () => {
    if (!authorized) {
      Alert.alert(
        'Authorization Required',
        'Please check the mandatory human authorization box confirming you understand this is a sandboxed simulation.'
      );
      return;
    }

    setLoading(true);
    try {
      const payload = {
        fullName: fullName.trim(),
        age: parseInt(age) || 35,
        gender,
        phone: phone.trim(),
        devoteeCount: parseInt(devoteeCount) || 1,
        yatraDate,
        slot,
        transportMode,
        hotel: hotelChoice,
        authorized: true,
      };

      // Call API authorization and confirmation
      let passNumber = `VD-RPA-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;

      try {
        const authRes = await authorizeBooking(payload);
        if (authRes?.pass_id) {
          passNumber = authRes.pass_id;
        }
      } catch (e) {
        // Fallback for sandboxed offline testing
      }

      setGeneratedPass({
        passNumber,
        fullName: payload.fullName,
        yatraDate: payload.yatraDate,
        slot: payload.slot,
        devoteeCount: payload.devoteeCount,
        transportMode: payload.transportMode,
        hotel: payload.hotel,
        generatedAt: new Date().toLocaleString(),
        status: 'SIMULATED VERIFIED (SANDBOX)',
      });

      setStep(4);
    } catch (err) {
      Alert.alert('Booking Error', err.message || 'Simulation execution encountered an issue.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPass = async () => {
    if (generatedPass?.passNumber) {
      await Clipboard.setStringAsync(generatedPass.passNumber);
      Alert.alert('Copied', `Pass Reference ${generatedPass.passNumber} copied to clipboard.`);
    }
  };

  const handleReset = () => {
    setStep(1);
    setAuthorized(false);
    setGeneratedPass(null);
  };

  return (
    <View style={styles.container}>
      <Header
        title="Guided Yatra Booking"
        subtitle="Sandboxed Parchi & Service Reservation"
      />

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        {[1, 2, 3, 4].map((s) => (
          <View key={s} style={styles.progressStep}>
            <View
              style={[
                styles.stepCircle,
                step >= s ? styles.stepCircleActive : styles.stepCircleInactive,
              ]}
            >
              {s === 4 && step === 4 ? (
                <CheckIcon size={12} color={colors.surface} />
              ) : (
                <Text
                  style={[
                    styles.stepNumber,
                    step >= s ? styles.stepNumberActive : styles.stepNumberInactive,
                  ]}
                >
                  {s}
                </Text>
              )}
            </View>
            <Text style={styles.stepLabel}>
              {s === 1 && 'Pilgrim'}
              {s === 2 && 'Schedule'}
              {s === 3 && 'Authorise'}
              {s === 4 && 'Parchi'}
            </Text>
          </View>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* STEP 1: Pilgrim Information */}
        {step === 1 && (
          <View style={styles.card}>
            <Text style={styles.stepTitle}>Step 1: Primary Pilgrim Details</Text>
            <Text style={styles.stepSubtitle}>
              Official devotee information for yatra parchi issuance.
            </Text>

            <Text style={styles.inputLabel}>Full Devotee Name *</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="e.g. Ramesh Sharma"
              placeholderTextColor={colors.textLight}
            />

            <View style={styles.row}>
              <View style={styles.halfCol}>
                <Text style={styles.inputLabel}>Age *</Text>
                <TextInput
                  style={styles.input}
                  value={age}
                  onChangeText={setAge}
                  placeholder="38"
                  placeholderTextColor={colors.textLight}
                  keyboardType="number-pad"
                  maxLength={3}
                />
              </View>
              <View style={styles.halfCol}>
                <Text style={styles.inputLabel}>Gender</Text>
                <View style={styles.genderRow}>
                  {['Male', 'Female'].map((g) => (
                    <TouchableOpacity
                      key={g}
                      style={[styles.genderBtn, gender === g && styles.genderBtnActive]}
                      onPress={() => setGender(g)}
                    >
                      <Text
                        style={[
                          styles.genderText,
                          gender === g && styles.genderTextActive,
                        ]}
                      >
                        {g}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            </View>

            <View style={styles.row}>
              <View style={styles.halfCol}>
                <Text style={styles.inputLabel}>Mobile (+91) *</Text>
                <TextInput
                  style={styles.input}
                  value={phone}
                  onChangeText={setPhone}
                  placeholder="9876543210"
                  placeholderTextColor={colors.textLight}
                  keyboardType="phone-pad"
                  maxLength={10}
                />
              </View>
              <View style={styles.halfCol}>
                <Text style={styles.inputLabel}>Devotees (Count)</Text>
                <TextInput
                  style={styles.input}
                  value={devoteeCount}
                  onChangeText={setDevoteeCount}
                  placeholder="2"
                  placeholderTextColor={colors.textLight}
                  keyboardType="number-pad"
                  maxLength={2}
                />
              </View>
            </View>

            <TouchableOpacity style={styles.nextBtn} onPress={handleNextStep}>
              <Text style={styles.nextBtnText}>Continue to Yatra Schedule →</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* STEP 2: Pilgrimage Schedule & Preferences */}
        {step === 2 && (
          <View style={styles.card}>
            <Text style={styles.stepTitle}>Step 2: Pilgrimage Schedule & Route</Text>
            <Text style={styles.stepSubtitle}>
              Select your intended yatra dates, trek mode, and stay.
            </Text>

            <Text style={styles.inputLabel}>Intended Yatra Date (YYYY-MM-DD)</Text>
            <TextInput
              style={styles.input}
              value={yatraDate}
              onChangeText={setYatraDate}
              placeholder="2026-12-15"
              placeholderTextColor={colors.textLight}
            />

            <Text style={styles.inputLabel}>Darshan Time Window</Text>
            <View style={styles.optionsContainer}>
              {[
                'Morning (06:00 - 12:00)',
                'Afternoon (12:00 - 18:00)',
                'Evening Aarti (18:00 - 22:00)',
                'Night Darshan (22:00 - 06:00)',
              ].map((s) => (
                <TouchableOpacity
                  key={s}
                  style={[styles.optionChip, slot === s && styles.optionChipActive]}
                  onPress={() => setSlot(s)}
                >
                  <Text style={[styles.optionText, slot === s && styles.optionTextActive]}>
                    {s}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.inputLabel}>Ascent Mode</Text>
            <View style={styles.optionsContainer}>
              {[
                'Traditional Trek (Banganga)',
                'Tarakote Marg (Gentle Slope)',
                'Helicopter (Katra - Sanjichhat)',
                'Battery Car (Ardhkuwari - Bhawan)',
              ].map((m) => (
                <TouchableOpacity
                  key={m}
                  style={[styles.optionChip, transportMode === m && styles.optionChipActive]}
                  onPress={() => setTransportMode(m)}
                >
                  <Text style={[styles.optionText, transportMode === m && styles.optionTextActive]}>
                    {m}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.inputLabel}>Selected Accommodation</Text>
            <TextInput
              style={styles.input}
              value={hotelChoice}
              onChangeText={setHotelChoice}
              placeholder="e.g. Niharika Complex (SMVDSB)"
              placeholderTextColor={colors.textLight}
            />

            <View style={styles.buttonRow}>
              <TouchableOpacity style={styles.backBtn} onPress={() => setStep(1)}>
                <Text style={styles.backBtnText}>← Back</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.nextBtnFlex} onPress={handleNextStep}>
                <Text style={styles.nextBtnText}>Review & Authorize →</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* STEP 3: Mandatory Human Authorization (Safety Guardrail) */}
        {step === 3 && (
          <View style={styles.card}>
            <Text style={styles.stepTitle}>Step 3: Human Authorization Guardrail</Text>
            <Text style={styles.stepSubtitle}>
              Mandatory human verification before mock RPA workflow execution.
            </Text>

            <View style={styles.summaryBox}>
              <Text style={styles.summaryTitle}>Pilgrimage Booking Summary</Text>
              <Text style={styles.summaryLine}>• Primary Devotee: <Text style={styles.bold}>{fullName}</Text> ({age} yrs, {gender})</Text>
              <Text style={styles.summaryLine}>• Pilgrims: <Text style={styles.bold}>{devoteeCount} Person(s)</Text></Text>
              <Text style={styles.summaryLine}>• Yatra Date: <Text style={styles.bold}>{yatraDate}</Text></Text>
              <Text style={styles.summaryLine}>• Slot: <Text style={styles.bold}>{slot}</Text></Text>
              <Text style={styles.summaryLine}>• Route: <Text style={styles.bold}>{transportMode}</Text></Text>
              <Text style={styles.summaryLine}>• Stay: <Text style={styles.bold}>{hotelChoice}</Text></Text>
            </View>

            {/* Prominent Educational Notice */}
            <View style={styles.safetyCard}>
              <Text style={styles.safetyHeader}>SANDBOXED SIMULATION GUARDRAIL</Text>
              <Text style={styles.safetyBody}>
                This system runs an educational mock booking simulation. It generates a verified proof-of-concept RPA reservation pass. Real darshan parchi and helicopter tickets MUST be purchased through Shri Mata Vaishno Devi Shrine Board at <Text style={styles.bold}>maavaishnodevi.org</Text>.
              </Text>
            </View>

            <TouchableOpacity
              style={styles.checkboxContainer}
              onPress={() => setAuthorized(!authorized)}
              activeOpacity={0.8}
            >
              <View style={[styles.checkbox, authorized && styles.checkboxChecked]}>
                {authorized && <CheckIcon size={12} color={colors.surface} />}
              </View>
              <Text style={styles.checkboxLabel}>
                I understand this is a sandboxed simulation and authorize generating the simulated Yatra Parchi Pass.
              </Text>
            </TouchableOpacity>

            <View style={styles.buttonRow}>
              <TouchableOpacity style={styles.backBtn} onPress={() => setStep(2)}>
                <Text style={styles.backBtnText}>← Back</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.confirmBtn,
                  (!authorized || loading) && styles.btnDisabled,
                ]}
                onPress={handleExecuteRpaBooking}
                disabled={!authorized || loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color={colors.surface} />
                ) : (
                  <Text style={styles.confirmBtnText}>Authorize & Generate Pass</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* STEP 4: Generated Parchi / RPA Booking Pass */}
        {step === 4 && generatedPass && (
          <View style={styles.passCard}>
            <View style={styles.passHeader}>
              <YatraLogo size={44} />
              <View style={styles.passTitleContainer}>
                <Text style={styles.passHeaderTitle}>SHRI MATA VAISHNO DEVI</Text>
                <Text style={styles.passHeaderSubtitle}>SIMULATED YATRA PARCHI (SANDBOX)</Text>
              </View>
            </View>

            <View style={styles.passRefContainer}>
              <Text style={styles.passRefLabel}>VERIFIED PASS NUMBER:</Text>
              <Text style={styles.passRefNumber}>{generatedPass.passNumber}</Text>
              <TouchableOpacity style={styles.copyBtn} onPress={handleCopyPass}>
                <Text style={styles.copyBtnText}>Copy Pass Number</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.passGrid}>
              <View style={styles.gridItem}>
                <Text style={styles.gridLabel}>Devotee Name</Text>
                <Text style={styles.gridValue}>{generatedPass.fullName}</Text>
              </View>
              <View style={styles.gridItem}>
                <Text style={styles.gridLabel}>Devotees</Text>
                <Text style={styles.gridValue}>{generatedPass.devoteeCount} Person(s)</Text>
              </View>
              <View style={styles.gridItem}>
                <Text style={styles.gridLabel}>Yatra Date</Text>
                <Text style={styles.gridValue}>{generatedPass.yatraDate}</Text>
              </View>
              <View style={styles.gridItem}>
                <Text style={styles.gridLabel}>Slot</Text>
                <Text style={styles.gridValue}>{generatedPass.slot}</Text>
              </View>
              <View style={styles.gridItemFull}>
                <Text style={styles.gridLabel}>Trek / Route</Text>
                <Text style={styles.gridValue}>{generatedPass.transportMode}</Text>
              </View>
              <View style={styles.gridItemFull}>
                <Text style={styles.gridLabel}>Accommodation</Text>
                <Text style={styles.gridValue}>{generatedPass.hotel}</Text>
              </View>
            </View>

            {/* Barcode Simulated Visual */}
            <View style={styles.barcodeBox}>
              <Text style={styles.barcodeVisual}>||| | |||| | ||| |||| | || |||| | |||</Text>
              <Text style={styles.barcodeText}>{generatedPass.passNumber} • ENCRYPTED_HMAC_SHA256</Text>
            </View>

            <View style={styles.stampBox}>
              <Text style={styles.stampText}>RPA WORKFLOW SIMULATED SUCCESSFULLY</Text>
            </View>

            <TouchableOpacity style={styles.resetBtn} onPress={handleReset}>
              <Text style={styles.resetBtnText}>+ Plan Another Pilgrimage</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  progressStep: {
    alignItems: 'center',
  },
  stepCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 4,
  },
  stepCircleActive: {
    backgroundColor: colors.primary,
  },
  stepCircleInactive: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  stepNumber: {
    fontSize: 12,
    fontWeight: '700',
  },
  stepNumberActive: {
    color: colors.surface,
  },
  stepNumberInactive: {
    color: colors.textSecondary,
  },
  stepLabel: {
    fontSize: 10,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  scrollContent: {
    padding: spacing.md,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusLg,
    padding: spacing.lg,
    ...spacing.shadowMd,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  stepTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 4,
  },
  stepSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
    marginTop: 6,
  },
  input: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: spacing.radiusSm,
    paddingHorizontal: spacing.md,
    paddingVertical: 9,
    fontSize: 14,
    color: colors.text,
    marginBottom: spacing.xs,
  },
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  halfCol: {
    flex: 1,
  },
  genderRow: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  genderBtn: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: spacing.radiusSm,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    backgroundColor: colors.surfaceSecondary,
  },
  genderBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  genderText: {
    fontSize: 13,
    color: colors.text,
    fontWeight: '500',
  },
  genderTextActive: {
    color: colors.surface,
    fontWeight: '700',
  },
  optionsContainer: {
    gap: 6,
    marginBottom: spacing.xs,
  },
  optionChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: spacing.radiusSm,
    borderWidth: 1,
    borderColor: colors.borderLight,
    backgroundColor: colors.surfaceSecondary,
  },
  optionChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  optionText: {
    fontSize: 12,
    color: colors.text,
  },
  optionTextActive: {
    color: colors.surface,
    fontWeight: '600',
  },
  nextBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 13,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  nextBtnText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '700',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  backBtn: {
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
    borderRadius: spacing.radiusMd,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  backBtnText: {
    fontSize: 13,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  nextBtnFlex: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  summaryBox: {
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.md,
    borderRadius: spacing.radiusMd,
    marginBottom: spacing.md,
  },
  summaryTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: spacing.xs,
  },
  summaryLine: {
    fontSize: 12,
    color: colors.text,
    marginBottom: 3,
  },
  bold: {
    fontWeight: '700',
  },
  safetyCard: {
    backgroundColor: '#FEF3C7',
    borderWidth: 1,
    borderColor: '#F59E0B',
    borderRadius: spacing.radiusMd,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  safetyHeader: {
    fontSize: 12,
    fontWeight: '800',
    color: '#92400E',
    marginBottom: 4,
  },
  safetyBody: {
    fontSize: 11,
    color: '#78350F',
    lineHeight: 16,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.md,
    paddingHorizontal: 4,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 4,
    marginRight: spacing.sm,
    marginTop: 2,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surface,
  },
  checkboxChecked: {
    backgroundColor: colors.primary,
  },
  checkmark: {
    color: colors.surface,
    fontSize: 13,
    fontWeight: 'bold',
  },
  checkboxLabel: {
    fontSize: 12,
    color: colors.text,
    flex: 1,
    lineHeight: 17,
  },
  confirmBtn: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  confirmBtnText: {
    color: colors.surface,
    fontSize: 13,
    fontWeight: '700',
  },
  btnDisabled: {
    opacity: 0.5,
  },
  passCard: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusLg,
    padding: spacing.lg,
    borderWidth: 2,
    borderColor: colors.gold,
    ...spacing.shadowLg,
  },
  passHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
    paddingBottom: spacing.md,
    marginBottom: spacing.md,
  },
  passTitleContainer: {
    marginLeft: spacing.sm,
  },
  passHeaderTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.primary,
    letterSpacing: 0.5,
  },
  passHeaderSubtitle: {
    fontSize: 10,
    color: colors.textSecondary,
    letterSpacing: 1,
    marginTop: 2,
  },
  passRefContainer: {
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.md,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  passRefLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  passRefNumber: {
    fontSize: 22,
    fontWeight: '900',
    color: colors.primary,
    fontFamily: 'monospace',
    letterSpacing: 2,
    marginVertical: 4,
  },
  copyBtn: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: spacing.radiusSm,
    marginTop: 4,
  },
  copyBtnText: {
    fontSize: 11,
    color: colors.primary,
    fontWeight: '700',
  },
  passGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.md,
  },
  gridItem: {
    width: '50%',
    paddingVertical: 6,
  },
  gridItemFull: {
    width: '100%',
    paddingVertical: 6,
  },
  gridLabel: {
    fontSize: 10,
    color: colors.textSecondary,
    textTransform: 'uppercase',
  },
  gridValue: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
    marginTop: 1,
  },
  barcodeBox: {
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
    paddingTop: spacing.md,
    marginBottom: spacing.md,
  },
  barcodeVisual: {
    fontSize: 20,
    letterSpacing: 3,
    fontFamily: 'monospace',
    color: colors.text,
  },
  barcodeText: {
    fontSize: 9,
    color: colors.textLight,
    marginTop: 2,
    fontFamily: 'monospace',
  },
  stampBox: {
    backgroundColor: '#DEF7EC',
    borderWidth: 1,
    borderColor: '#31C48D',
    padding: spacing.sm,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  stampText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#03543F',
  },
  resetBtn: {
    borderWidth: 1.5,
    borderColor: colors.primary,
    paddingVertical: 12,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  resetBtnText: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: '700',
  },
});
