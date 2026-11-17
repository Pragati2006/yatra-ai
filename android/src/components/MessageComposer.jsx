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
} from 'react-native';
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

  return (
    <View style={styles.container}>
      {/* Quick Suggestion Chips */}
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
          <GlobeIcon size={12} color={colors.burgundy} strokeWidth={2} />
          <Text style={styles.langPillText}>{activeLang.label.slice(0, 2).toUpperCase()}</Text>
        </TouchableOpacity>

        {/* High-Contrast Visible Input */}
        <TextInput
          ref={inputRef}
          style={styles.input}
          placeholder={
            micState === 'listening' ? 'Listening... Speak now' : "Ask Yatra AI (e.g. 'How to reach Bhawan?')"
          }
          placeholderTextColor={colors.textPlaceholder}
          value={text}
          onChangeText={setText}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          multiline
          maxLength={1000}
          editable={!isBusy}
          cursorColor={colors.burgundy}
          selectionColor={colors.goldBorder}
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
            <MicIcon size={18} color={colors.burgundy} strokeWidth={2.2} />
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
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: colors.goldBorder,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  chipsContainer: {
    flexDirection: 'row',
    paddingBottom: 8,
    gap: 6,
  },
  chip: {
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 14,
  },
  chipText: {
    fontSize: 12,
    color: colors.burgundy,
    fontWeight: '700',
  },
  statusBanner: {
    backgroundColor: '#FFF9F0',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginBottom: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusBannerListening: {
    backgroundColor: '#FFF0F0',
    borderColor: '#C0392B',
  },
  statusBannerError: {
    backgroundColor: '#FFF0F0',
    borderColor: '#E74C3C',
  },
  statusBannerCompleted: {
    backgroundColor: '#F0FDF4',
    borderColor: '#16A34A',
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
    backgroundColor: '#C0392B',
  },
  statusText: {
    fontSize: 11,
    color: colors.burgundy,
    fontWeight: '700',
    flex: 1,
  },
  stopBtn: {
    backgroundColor: '#C0392B',
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
    color: colors.burgundy,
    fontWeight: '700',
  },
  langList: {
    gap: 6,
  },
  langChip: {
    backgroundColor: colors.bgSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    paddingVertical: 2,
    paddingHorizontal: 8,
  },
  langChipActive: {
    backgroundColor: colors.burgundy,
    borderColor: colors.burgundy,
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
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: colors.goldBorder,
    borderRadius: 22,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  inputRowFocused: {
    borderColor: colors.gold,
  },
  inputRowListening: {
    borderColor: '#C0392B',
    backgroundColor: '#FFF9F9',
  },
  langPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 4,
    paddingHorizontal: 7,
    borderRadius: 10,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    marginRight: 4,
    marginBottom: 5,
  },
  langPillText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.burgundy,
  },
  input: {
    flex: 1,
    fontSize: 15,
    lineHeight: 20,
    color: colors.text,
    minHeight: 40,
    maxHeight: 110,
    paddingTop: 8,
    paddingBottom: 8,
    paddingHorizontal: 4,
    textAlignVertical: 'top',
    fontWeight: '500',
  },
  micButton: {
    backgroundColor: colors.goldSubtle,
    borderWidth: 1.2,
    borderColor: colors.goldBorder,
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 4,
    marginBottom: 3,
  },
  micButtonActive: {
    backgroundColor: '#C0392B',
    borderColor: '#962D22',
  },
  sendButton: {
    backgroundColor: colors.burgundy,
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 6,
    marginBottom: 3,
  },
  sendButtonDisabled: {
    backgroundColor: '#CCCCCC',
    opacity: 0.6,
  },
});
