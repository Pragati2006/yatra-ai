import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  ScrollView,
  Platform,
  Alert,
  ActivityIndicator,
  Keyboard,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import {
  MicIcon,
  SquareIcon,
  SendIcon,
  GlobeIcon,
  AlertCircleIcon,
  CheckIcon,
} from './Icons';

const DEFAULT_PROMPTS = [
  'Delhi to Katra transport',
  'Bhairon Ghati altitude & tips',
  'Current weather at Bhawan',
  'Shrine Board accommodation',
  'Book Darshan slot',
];

const SUPPORTED_LANGUAGES = [
  { code: 'en-IN', label: 'English (IN)' },
  { code: 'hi-IN', label: 'Hindi (हिंदी)' },
  { code: 'pa-IN', label: 'Punjabi (ਪੰਜਾਬੀ)' },
  { code: 'ur-IN', label: 'Urdu (اردو)' },
];

export default function MessageComposer({ onSend, isLoading, disabled, suggestions = [] }) {
  const insets = useSafeAreaInsets();
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);
  const [text, setText] = useState('');
  const [micState, setMicState] = useState('idle'); // 'idle' | 'listening' | 'processing' | 'completed' | 'error'
  const [micStatus, setMicStatus] = useState('');
  const [selectedLang, setSelectedLang] = useState('en-IN');
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);

  const isBusy = isLoading || disabled;
  const chipList = suggestions && suggestions.length > 0 ? suggestions : DEFAULT_PROMPTS;

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const showSub = Keyboard.addListener(showEvent, () => setIsKeyboardVisible(true));
    const hideSub = Keyboard.addListener(hideEvent, () => setIsKeyboardVisible(false));
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const handleSend = () => {
    if (!text.trim() || isBusy) return;
    if (micState === 'listening') {
      stopListening();
    }
    onSend(text.trim());
    setText('');
    setMicStatus('');
    setMicState('idle');
  };

  const handleSelectPrompt = (prompt) => {
    if (isBusy) return;
    if (micState === 'listening') {
      stopListening();
    }
    onSend(prompt);
    setMicStatus('');
    setMicState('idle');
  };

  const stopListening = () => {
    setMicState('idle');
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
  };

  const handleMicPress = () => {
    if (isBusy) return;

    // Toggle off if already listening
    if (micState === 'listening') {
      stopListening();
      setMicStatus('');
      return;
    }

    // 1. Web Platform (Expo Web) -> Web Speech API
    if (Platform.OS === 'web') {
      const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
      if (!SR) {
        setMicState('error');
        setMicStatus('Speech recognition is not supported in this browser.');
        setTimeout(() => {
          setMicState('idle');
          setMicStatus('');
        }, 4000);
        return;
      }

      try {
        const recognition = new SR();
        recognition.lang = selectedLang;
        recognition.interimResults = true;
        recognitionRef.current = recognition;

        recognition.onstart = () => {
          setMicState('listening');
          const langObj = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLang);
          setMicStatus(`Listening in ${langObj?.label || 'English'}... Speak now.`);
        };

        recognition.onresult = (event) => {
          let interim = '';
          let final = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript;
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          const speech = final || interim;
          if (speech) {
            setText((prev) => (prev ? `${prev.trim()} ${speech}` : speech));
          }
          if (final) {
            setMicState('completed');
            setMicStatus(`Transcribed: "${final.trim()}"`);
            setTimeout(() => {
              setMicState('idle');
              setMicStatus('');
            }, 3500);
          }
        };

        recognition.onerror = (e) => {
          setMicState('error');
          setMicStatus(`Recognition notice: ${e.error}`);
          setTimeout(() => {
            setMicState('idle');
            setMicStatus('');
          }, 4000);
        };

        recognition.onend = () => {
          if (micState === 'listening') {
            setMicState('idle');
          }
        };

        recognition.start();
      } catch (err) {
        setMicState('error');
        setMicStatus('Could not access microphone.');
        setTimeout(() => {
          setMicState('idle');
          setMicStatus('');
        }, 4000);
      }
      return;
    }

    // 2. Native Android / iOS Platform (Expo Go Runtime)
    // Clear platform distinction: system keyboard voice typing is standard in Expo Go
    inputRef.current?.focus();
    setMicStatus('Tap the microphone on your keyboard to speak in Hindi, English, Punjabi, or Urdu.');
    setTimeout(() => setMicStatus(''), 6000);

    Alert.alert(
      'Devotee Voice Input',
      'In Expo Go, voice typing is powered by your Android system keyboard (Gboard / Samsung Voice Typing):\n\n1. Your keyboard is now open.\n2. Tap the microphone icon on your keyboard spacebar or top toolbar.\n3. Speak in Hindi, English, Punjabi, or Urdu.\n4. Your words will appear instantly in the chat input.\n\n(Review and edit your text before sending).',
      [{ text: 'Got it', onPress: () => inputRef.current?.focus() }]
    );
  };

  const activeLang = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLang) || SUPPORTED_LANGUAGES[0];
  const bottomInsetPadding = isKeyboardVisible ? 6 : Math.max(insets.bottom, 10);

  return (
    <View style={[styles.container, { paddingBottom: bottomInsetPadding }]}>
      {/* Quick Suggestion Chips (hidden when keyboard is open to maximize chat view) */}
      {!isKeyboardVisible && chipList.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsContainer}
          keyboardShouldPersistTaps="handled"
        >
          {chipList.map((p, idx) => (
            <TouchableOpacity
              key={idx}
              style={styles.chip}
              onPress={() => handleSelectPrompt(p)}
              disabled={isBusy}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText}>{p}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Voice Status & Guidance Banner */}
      {micStatus ? (
        <View
          style={[
            styles.statusBanner,
            micState === 'listening'
              ? styles.statusBannerListening
              : micState === 'error'
              ? styles.statusBannerError
              : micState === 'completed'
              ? styles.statusBannerCompleted
              : null,
          ]}
        >
          <View style={styles.statusLeft}>
            {micState === 'listening' ? (
              <View style={styles.listeningDot} />
            ) : micState === 'error' ? (
              <AlertCircleIcon size={14} color="#C0392B" />
            ) : micState === 'completed' ? (
              <CheckIcon size={14} color="#15803D" />
            ) : null}
            <Text style={styles.statusText} numberOfLines={2}>
              {micStatus}
            </Text>
          </View>
          {micState === 'listening' && (
            <TouchableOpacity onPress={stopListening} style={styles.stopBtn} activeOpacity={0.8}>
              <SquareIcon size={10} color="#FFFFFF" />
              <Text style={styles.stopBtnText}>Stop</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : null}

      {/* Language Selector Bar */}
      {showLangMenu && (
        <View style={styles.langBar}>
          <Text style={styles.langBarLabel}>Voice Language:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.langList}>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <TouchableOpacity
                key={lang.code}
                style={[styles.langChip, selectedLang === lang.code && styles.langChipActive]}
                onPress={() => {
                  setSelectedLang(lang.code);
                  setShowLangMenu(false);
                }}
              >
                <Text style={[styles.langChipText, selectedLang === lang.code && styles.langChipTextActive]}>
                  {lang.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Main Input Row: Language Pill + Text Input + Microphone Button + Send Button */}
      <View
        style={[
          styles.inputRow,
          isFocused && styles.inputRowFocused,
          micState === 'listening' && styles.inputRowListening,
        ]}
      >
        <TouchableOpacity
          style={styles.langPill}
          onPress={() => setShowLangMenu((prev) => !prev)}
          activeOpacity={0.7}
          hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
          accessibilityLabel="Select voice language"
        >
          <GlobeIcon size={12} color={colors.royalPlum} strokeWidth={2} />
          <Text style={styles.langPillText}>{activeLang.label.slice(0, 2).toUpperCase()}</Text>
        </TouchableOpacity>

        {/* High-Contrast Visible Input */}
        <TextInput
          ref={inputRef}
          style={styles.input}
          placeholder={
            micState === 'listening' ? 'Listening... Speak now' : "Ask Yatra AI (e.g. 'How to reach Bhawan?')"
          }
          placeholderTextColor={colors.textMuted}
          value={text}
          onChangeText={setText}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          multiline
          maxLength={1000}
          editable={!isBusy}
          cursorColor={colors.royalPlum}
          selectionColor={colors.softPlum}
          accessibilityLabel="Message input field"
        />

        {/* Recognizable Voice Input Microphone Button */}
        <TouchableOpacity
          style={[styles.micButton, micState === 'listening' && styles.micButtonActive]}
          onPress={handleMicPress}
          disabled={isBusy}
          activeOpacity={0.7}
          hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
          accessibilityLabel={micState === 'listening' ? 'Stop voice listening' : 'Start voice input'}
          accessibilityRole="button"
        >
          {micState === 'listening' ? (
            <SquareIcon size={14} color="#FFFFFF" />
          ) : (
            <MicIcon size={18} color={colors.royalPlum} strokeWidth={2.2} />
          )}
        </TouchableOpacity>

        {/* Send Button */}
        <TouchableOpacity
          style={[styles.sendButton, (!text.trim() || isBusy) && styles.sendButtonDisabled]}
          onPress={handleSend}
          disabled={!text.trim() || isBusy}
          hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
          accessibilityLabel="Send message"
        >
          <SendIcon size={15} color="#FFFFFF" strokeWidth={2.4} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
    paddingTop: 6,
    paddingHorizontal: 12,
  },
  chipsContainer: {
    flexDirection: 'row',
    paddingBottom: 8,
    gap: 6,
  },
  chip: {
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: 16,
    ...Platform.select({
      android: { elevation: 1 },
      ios: {
        shadowColor: '#54152D',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.03,
        shadowRadius: 2,
      },
    }),
  },
  chipText: {
    fontSize: 12,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  statusBanner: {
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    borderRadius: 12,
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginBottom: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusBannerListening: {
    backgroundColor: '#FAEBEC',
    borderColor: colors.danger,
  },
  statusBannerError: {
    backgroundColor: '#FAEBEC',
    borderColor: colors.danger,
  },
  statusBannerCompleted: {
    backgroundColor: '#E8F5EE',
    borderColor: colors.success,
  },
  statusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flex: 1,
  },
  listeningDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.danger,
  },
  statusText: {
    fontSize: 11,
    color: colors.royalPlum,
    fontWeight: '700',
    flex: 1,
  },
  stopBtn: {
    backgroundColor: colors.danger,
    borderRadius: 10,
    paddingVertical: 3,
    paddingHorizontal: 8,
    marginLeft: 6,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  stopBtnText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '800',
  },
  langBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
    marginBottom: 6,
    gap: 6,
  },
  langBarLabel: {
    fontSize: 11,
    color: colors.royalPlum,
    fontWeight: '700',
  },
  langList: {
    gap: 6,
  },
  langChip: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    borderRadius: 10,
    paddingVertical: 3,
    paddingHorizontal: 8,
  },
  langChipActive: {
    backgroundColor: colors.royalPlum,
    borderColor: colors.royalPlum,
  },
  langChipText: {
    fontSize: 10.5,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  langChipTextActive: {
    color: '#FFFFFF',
    fontWeight: '800',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1.5,
    borderColor: colors.borderDefault,
    borderRadius: 26,
    paddingHorizontal: 10,
    paddingVertical: 4,
    ...Platform.select({
      android: { elevation: 2 },
      ios: {
        shadowColor: '#54152D',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 5,
      },
    }),
  },
  inputRowFocused: {
    borderColor: colors.champagneTaupe,
  },
  inputRowListening: {
    borderColor: colors.danger,
    backgroundColor: '#FAEBEC',
  },
  langPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 4,
    paddingHorizontal: 7,
    borderRadius: 10,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    marginRight: 4,
    marginBottom: 5,
  },
  langPillText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.royalPlum,
  },
  input: {
    flex: 1,
    fontSize: 14.5,
    lineHeight: 20,
    color: colors.textPrimary,
    minHeight: 38,
    maxHeight: 120,
    paddingTop: 8,
    paddingBottom: 8,
    paddingHorizontal: 4,
    textAlignVertical: 'top',
    fontWeight: '500',
  },
  micButton: {
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 4,
    marginBottom: 3,
  },
  micButtonActive: {
    backgroundColor: colors.danger,
    borderColor: colors.danger,
  },
  sendButton: {
    backgroundColor: colors.royalPlum,
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 6,
    marginBottom: 3,
  },
  sendButtonDisabled: {
    backgroundColor: colors.warmBeige,
    opacity: 0.5,
  },
});
