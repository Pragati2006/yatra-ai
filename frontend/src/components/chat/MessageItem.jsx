import React from 'react';
import { User, RefreshCw, Volume2, Square } from 'lucide-react';
import MarkdownContent from './MarkdownContent';
import PersonalizedPlanCard from './cards/PersonalizedPlanCard';
import BookingHandoffCard from './cards/BookingHandoffCard';
import SightseeingAdvisoryCard from './cards/SightseeingAdvisoryCard';
import ItineraryCard from './cards/ItineraryCard';
import WeatherCard from './cards/WeatherCard';
import BudgetCard from './cards/BudgetCard';
import HotelMiniCard from './cards/HotelMiniCard';
import TransportMiniCard from './cards/TransportMiniCard';
import OperationalNoticeCard from './cards/OperationalNoticeCard';
import VerifiedContactCard from './cards/VerifiedContactCard';
import ProvenanceList from './provenance/ProvenanceList';
import YatraLogo from '../common/YatraLogo';

/**
 * Message item representing a single turn in the Yatra AI conversation.
 * Seamlessly hosts Markdown content and structured interactive cards.
 */
export default function MessageItem({
  message,
  index,
  isLatest,
  chatState,
  onSend,
  onNavigateToBooking,
  onSwitchToForm,
  onExplorePlace,
  latestMessageRef,
}) {
  const isUser = message.role === 'user';
  const hasContent = Boolean(message.content && message.content.trim().length > 0);
  const hasRecommendation = Boolean(message.recommendation);
  const hasInfeasible = Boolean(message.infeasible_places && message.infeasible_places.length > 0);
  const isBookingHandoff = message.action === 'NAVIGATE_TO_BOOKING' || message.status === 'NAVIGATE_TO_BOOKING';

  // Text-To-Speech for assistant
  const speakText = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const clean = text.replace(/<[^>]+>/g, ' ').replace(/[*#_`]/g, '');
    const utter = new SpeechSynthesisUtterance(clean);
    utter.rate = 0.95;
    window.speechSynthesis.speak(utter);
  };

  const stopSpeaking = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  return (
    <div
      ref={isLatest ? latestMessageRef : null}
      data-testid={`chat-message-${message.role}-${index}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        width: '100%',
        maxWidth: '820px',
        margin: '0 auto',
        padding: '0.35rem 0',
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: '10px',
          maxWidth: isUser ? '85%' : '100%',
          width: isUser ? 'auto' : '100%',
          flexDirection: isUser ? 'row-reverse' : 'row',
        }}
      >
        {/* Avatar badge */}
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: isUser ? 'var(--gold-subtle, #F5ECDA)' : 'transparent',
            border: isUser ? '1.5px solid var(--gold-border, #E5D2AD)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.85rem',
            color: 'var(--burgundy, #58111A)',
            flexShrink: 0,
            marginTop: '2px',
            boxShadow: isUser ? '0 2px 6px rgba(88, 17, 26, 0.08)' : 'none',
          }}
        >
          {isUser ? <User size={16} color="var(--burgundy)" /> : <YatraLogo size={32} />}
        </div>

        {/* Message bubble / container */}
        <div
          style={{
            flex: 1,
            minWidth: 0,
            background: isUser ? 'var(--gold-subtle, #F5ECDA)' : '#FFFFFF',
            border: `1px solid ${isUser ? '#E5D2AD' : 'var(--gold-border, #E5D2AD)'}`,
            borderRadius: isUser ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
            padding: '0.85rem 1.15rem',
            boxShadow: '0 2px 8px rgba(88, 17, 26, 0.04)',
            color: 'var(--text-dark, #2A2020)',
            wordBreak: 'break-word',
            overflowWrap: 'anywhere',
          }}
        >
          {/* Header label */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '6px',
            }}
          >
            <span
              style={{
                fontFamily: isUser ? 'var(--font-sans)' : 'var(--font-serif, Cinzel, serif)',
                fontWeight: 800,
                fontSize: '0.78rem',
                color: 'var(--burgundy, #58111A)',
                letterSpacing: '0.03em',
              }}
            >
              {isUser ? 'You (Devotee)' : 'Yatra AI Companion'}
            </span>
            {message.created_at && (
              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted, #6B5C5C)' }}>
                {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          {/* 1. Markdown Narrative Text */}
          {hasContent && (
            <div data-testid="chat-message-text">
              <MarkdownContent content={message.content} />
            </div>
          )}

          {/* 1.1 Verified Source Attribution & Freshness Indicators */}
          {!isUser && (
            <ProvenanceList message={message} />
          )}

          {/* 2. Sightseeing Advisory (when present) */}
          {hasInfeasible && (
            <SightseeingAdvisoryCard infeasiblePlaces={message.infeasible_places} />
          )}

          {/* 3. Personalized Recommendation Card */}
          {hasRecommendation && (
            <div data-testid="chat-recommendation-block">
              <PersonalizedPlanCard
                recommendation={message.recommendation}
                message={message}
                chatState={chatState}
                onSend={onSend}
                onNavigateToBooking={onNavigateToBooking}
                onSwitchToForm={onSwitchToForm}
                onExplorePlace={onExplorePlace}
              />
            </div>
          )}

          {/* 4. Booking Handoff Card */}
          {isBookingHandoff && (
            <BookingHandoffCard
              message={message}
              chatState={chatState}
              onNavigateToBooking={onNavigateToBooking}
              onSwitchToForm={onSwitchToForm}
            />
          )}

          {/* 5. Itinerary Timeline Card (if separate itinerary attached) */}
          {message.itinerary && !hasRecommendation && (
            <ItineraryCard itinerary={message.itinerary} />
          )}

          {/* 6. Weather Card (if separate weather attached) */}
          {message.weather && (
            <WeatherCard weatherData={message.weather} />
          )}

          {/* 7. Hotel Mini Card (if single hotel recommendation attached) */}
          {message.hotel && !hasRecommendation && !isBookingHandoff && (
            <HotelMiniCard hotel={message.hotel} />
          )}

          {/* 8. Transport Mini Card (if single transport option attached) */}
          {message.selected_option && !hasRecommendation && !isBookingHandoff && (
            <TransportMiniCard option={message.selected_option} />
          )}

          {/* 9. Budget Evaluation Card */}
          {message.budget_evaluation && !hasRecommendation && !isBookingHandoff && (
            <BudgetCard budgetEvaluation={message.budget_evaluation} />
          )}

          {/* 10. Operational Notices Card */}
          {(message.operational_notices || message.operational_notice) && (
            <OperationalNoticeCard noticesData={message.operational_notices || message.operational_notice} />
          )}

          {/* 11. Verified Contacts Card */}
          {(message.verified_contacts || message.verified_contact) && (
            <VerifiedContactCard contactsData={message.verified_contacts || message.verified_contact} />
          )}

          {/* 10. Recoverable Error Retry Button */}
          {message.isError && message.failedQuery && (
            <div style={{ marginTop: '8px' }}>
              <button
                type="button"
                data-testid="chat-message-retry-btn"
                onClick={() => onSend(message.failedQuery)}
                className="btn btn-secondary"
                style={{
                  padding: '4px 12px',
                  fontSize: '0.76rem',
                  borderRadius: '6px',
                  border: '1px solid #C0392B',
                  color: '#721C24',
                  background: '#FFF5F5',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <RefreshCw size={12} />
                <span>Retry Message</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* TTS Audio Controls for Assistant */}
      {!isUser && hasContent && (
        <div style={{ display: 'flex', gap: '8px', marginTop: '4px', paddingLeft: '44px' }}>
          <button
            type="button"
            onClick={() => speakText(message.content)}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '0.72rem',
              color: 'var(--burgundy, #58111A)',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Volume2 size={13} />
            <span>Listen</span>
          </button>
          <button
            type="button"
            onClick={stopSpeaking}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '0.72rem',
              color: 'var(--text-muted, #6B5C5C)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Square size={11} fill="currentColor" />
            <span>Stop</span>
          </button>
        </div>
      )}
    </div>
  );
}
