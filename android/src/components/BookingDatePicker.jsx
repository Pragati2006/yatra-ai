import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import { ClockIcon, CheckIcon, CloseIcon } from './Icons';

/**
 * Format Date helper avoiding UTC timezone offset shifts
 */
export const formatDateToYMD = (d) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const parseYMDToDate = (ymdStr) => {
  if (!ymdStr) return new Date();
  const parts = String(ymdStr).split('-');
  if (parts.length === 3) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    return new Date(y, m, d);
  }
  return new Date();
};

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const DAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

export default function BookingDatePicker({
  value,
  onChange,
  minDate,
  label = 'Start Date (YYYY-MM-DD) *',
}) {
  const [modalVisible, setModalVisible] = useState(false);

  // Compute today's YMD
  const today = new Date();
  const todayYMD = formatDateToYMD(today);
  const effectiveMinYMD = minDate || todayYMD;

  // Selected date
  const selectedYMD = value || todayYMD;
  const initialDate = parseYMDToDate(selectedYMD);

  // Month navigation view state
  const [viewYear, setViewYear] = useState(initialDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(initialDate.getMonth()); // 0-indexed

  // Format display string
  const formatDisplayString = (ymd) => {
    try {
      const d = parseYMDToDate(ymd);
      const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
      const monthName = MONTH_NAMES[d.getMonth()].slice(0, 3);
      return `${dayName}, ${d.getDate()} ${monthName} ${d.getFullYear()}`;
    } catch {
      return ymd;
    }
  };

  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  const handleSelectDay = (dayNum) => {
    const candidate = new Date(viewYear, viewMonth, dayNum);
    const candidateYMD = formatDateToYMD(candidate);

    // Reject past dates
    if (candidateYMD < effectiveMinYMD) {
      return;
    }

    if (onChange) {
      onChange(candidateYMD);
    }
    setModalVisible(false);
  };

  // Build calendar matrix for viewed month
  const firstDayOfMonth = new Date(viewYear, viewMonth, 1).getDay(); // 0 for Sunday
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

  const calendarDays = [];
  // Empty slots before month start
  for (let i = 0; i < firstDayOfMonth; i++) {
    calendarDays.push({ key: `empty-${i}`, dayNum: null, disabled: true });
  }
  // Days of month
  for (let d = 1; d <= daysInMonth; d++) {
    const candidate = new Date(viewYear, viewMonth, d);
    const candidateYMD = formatDateToYMD(candidate);
    const isPast = candidateYMD < effectiveMinYMD;
    const isSelected = candidateYMD === selectedYMD;
    const isToday = candidateYMD === todayYMD;

    calendarDays.push({
      key: `day-${d}`,
      dayNum: d,
      ymd: candidateYMD,
      disabled: isPast,
      isSelected,
      isToday,
    });
  }

  // Can user navigate backwards? Disable if viewMonth/viewYear is earlier or equal to minDate's month
  const minDateObj = parseYMDToDate(effectiveMinYMD);
  const isAtOrBeforeMinMonth =
    viewYear < minDateObj.getFullYear() ||
    (viewYear === minDateObj.getFullYear() && viewMonth <= minDateObj.getMonth());

  return (
    <View style={styles.container}>
      {label ? <Text style={styles.label}>{label}</Text> : null}

      {/* Visible Interactive Date Selector Trigger */}
      <TouchableOpacity
        style={styles.datePickerTrigger}
        onPress={() => {
          const cur = parseYMDToDate(selectedYMD);
          setViewYear(cur.getFullYear());
          setViewMonth(cur.getMonth());
          setModalVisible(true);
        }}
        activeOpacity={0.8}
        accessibilityRole="button"
        accessibilityLabel={`Select Yatra date, currently ${selectedYMD}`}
      >
        <View style={styles.triggerLeft}>
          <ClockIcon size={16} color={colors.burgundy} />
          <View style={{ marginLeft: 8 }}>
            <Text style={styles.dateDisplayMain}>{formatDisplayString(selectedYMD)}</Text>
            <Text style={styles.dateDisplayRaw}>{selectedYMD}</Text>
          </View>
        </View>
        <View style={styles.changeBadge}>
          <Text style={styles.changeBadgeText}>Calendar 📅</Text>
        </View>
      </TouchableOpacity>

      {/* Native-compatible Calendar Modal */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.calendarCard}>
            {/* Calendar Header */}
            <View style={styles.calendarHeader}>
              <View>
                <Text style={styles.calendarTitle}>Select Yatra Start Date</Text>
                <Text style={styles.calendarSubtitle}>Past dates cannot be selected</Text>
              </View>
              <TouchableOpacity
                onPress={() => setModalVisible(false)}
                style={styles.closeBtn}
                accessibilityLabel="Close date picker"
              >
                <CloseIcon size={18} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            {/* Month & Year Navigation Bar */}
            <View style={styles.monthNavRow}>
              <TouchableOpacity
                onPress={handlePrevMonth}
                disabled={isAtOrBeforeMinMonth}
                style={[styles.navArrowBtn, isAtOrBeforeMinMonth && styles.navArrowBtnDisabled]}
                accessibilityLabel="Previous month"
              >
                <Text style={[styles.navArrowText, isAtOrBeforeMinMonth && styles.navArrowTextDisabled]}>
                  ‹
                </Text>
              </TouchableOpacity>

              <Text style={styles.monthTitleText}>
                {MONTH_NAMES[viewMonth]} {viewYear}
              </Text>

              <TouchableOpacity
                onPress={handleNextMonth}
                style={styles.navArrowBtn}
                accessibilityLabel="Next month"
              >
                <Text style={styles.navArrowText}>›</Text>
              </TouchableOpacity>
            </View>

            {/* Weekday Labels Header */}
            <View style={styles.weekdayRow}>
              {DAY_LABELS.map((d, idx) => (
                <Text key={idx} style={styles.weekdayLabel}>
                  {d}
                </Text>
              ))}
            </View>

            {/* Calendar Days Grid */}
            <View style={styles.gridContainer}>
              {calendarDays.map((item) => {
                if (item.dayNum === null) {
                  return <View key={item.key} style={styles.dayCellEmpty} />;
                }

                return (
                  <TouchableOpacity
                    key={item.key}
                    style={[
                      styles.dayCell,
                      item.isSelected && styles.dayCellSelected,
                      item.isToday && !item.isSelected && styles.dayCellToday,
                      item.disabled && styles.dayCellDisabled,
                    ]}
                    onPress={() => !item.disabled && handleSelectDay(item.dayNum)}
                    disabled={item.disabled}
                    activeOpacity={0.7}
                    accessibilityLabel={`${item.dayNum} ${MONTH_NAMES[viewMonth]} ${viewYear}${item.disabled ? ', disabled past date' : ''}`}
                  >
                    <Text
                      style={[
                        styles.dayNumberText,
                        item.isSelected && styles.dayNumberSelected,
                        item.isToday && !item.isSelected && styles.dayNumberToday,
                        item.disabled && styles.dayNumberDisabled,
                      ]}
                    >
                      {item.dayNum}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Bottom Actions */}
            <View style={styles.footerRow}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setModalVisible(false)}
                activeOpacity={0.7}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.confirmBtn}
                onPress={() => setModalVisible(false)}
                activeOpacity={0.85}
              >
                <CheckIcon size={14} color="#FFFFFF" />
                <Text style={styles.confirmBtnText}>Confirm ({selectedYMD})</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    marginBottom: 8,
  },
  label: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.burgundy,
    marginBottom: 5,
  },
  datePickerTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1.2,
    borderColor: colors.borderLight,
    borderRadius: spacing.radiusSm,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  triggerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  dateDisplayMain: {
    fontSize: 13.5,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  dateDisplayRaw: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 1,
  },
  changeBadge: {
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  changeBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.burgundy,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(26, 12, 18, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  calendarCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: colors.surface,
    borderRadius: 16,
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
    padding: 16,
    shadowColor: '#58111A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 6,
  },
  calendarHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  calendarTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: colors.burgundy,
  },
  calendarSubtitle: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  closeBtn: {
    padding: 4,
  },
  monthNavRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  monthTitleText: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.textPrimary,
    letterSpacing: 0.3,
  },
  navArrowBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.goldSubtle,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  navArrowBtnDisabled: {
    backgroundColor: colors.bgSubtle,
    borderColor: colors.borderLight,
    opacity: 0.4,
  },
  navArrowText: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.burgundy,
    marginTop: -2,
  },
  navArrowTextDisabled: {
    color: colors.textLight,
  },
  weekdayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
    paddingHorizontal: 2,
  },
  weekdayLabel: {
    width: 40,
    textAlign: 'center',
    fontSize: 11.5,
    fontWeight: '700',
    color: colors.goldDark,
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  dayCellEmpty: {
    width: 40,
    height: 38,
    marginVertical: 2,
  },
  dayCell: {
    width: 40,
    height: 38,
    marginVertical: 2,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayCellSelected: {
    backgroundColor: colors.burgundy,
  },
  dayCellToday: {
    borderWidth: 1.5,
    borderColor: colors.goldDark,
  },
  dayCellDisabled: {
    opacity: 0.3,
  },
  dayNumberText: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  dayNumberSelected: {
    color: colors.textWhite,
    fontWeight: '800',
  },
  dayNumberToday: {
    color: colors.burgundy,
    fontWeight: '800',
  },
  dayNumberDisabled: {
    color: colors.textLight,
    textDecorationLine: 'line-through',
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 10,
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  cancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  cancelBtnText: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  confirmBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.burgundy,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  confirmBtnText: {
    fontSize: 12.5,
    fontWeight: '800',
    color: colors.textWhite,
  },
});

