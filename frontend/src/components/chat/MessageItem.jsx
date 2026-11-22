import React, { useState } from 'react';
import { User, RefreshCw, Volume2, Square, ChevronDown, ChevronUp, Building2 } from 'lucide-react';
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
import InlineDatePickerCard from './cards/InlineDatePickerCard';
import DestinationGalleryCard from './cards/DestinationGalleryCard';
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
  const [showAllHotels, setShowAllHotels] = useState(false);
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
      data-is-streaming={Boolean(message.isStreaming)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        width: '100%',
        maxWidth: '820px',
        margin: '0 auto',
        padding: isUser ? '0.5rem 0' : '0.85rem 0',
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: '12px',
          maxWidth: isUser ? '82%' : '100%',
          width: isUser ? 'auto' : '100%',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-start',
        }}
      >
        {/* Avatar badge */}
        <div
          style={{
            width: '30px',
            height: '30px',
            borderRadius: '50%',
            background: isUser ? 'var(--soft-plum-surface, #F0E3E7)' : 'transparent',
            border: isUser ? '1px solid var(--border-default, #E9DED6)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.85rem',
            color: 'var(--royal-plum, #54152D)',
            flexShrink: 0,
            marginTop: '2px',
          }}
        >
          {isUser ? <User size={15} color="var(--royal-plum, #54152D)" /> : <YatraLogo size={28} />}
        </div>

        {/* Message bubble / container (Chat-first modern layout: Clean surface for assistant, soft bubble for user) */}
        <div
          style={{
            flex: 1,
            minWidth: 0,
            background: isUser ? 'var(--soft-plum-surface, #F0E3E7)' : 'transparent',
            border: isUser ? '1px solid var(--border-default, #E9DED6)' : 'none',
            borderRadius: isUser ? '20px 20px 4px 20px' : '0',
            padding: isUser ? '0.85rem 1.25rem' : '0.2rem 0',
            boxShadow: isUser ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
            color: 'var(--text-primary, #30272A)',
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
              marginBottom: isUser ? '4px' : '8px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-sans)',
                fontWeight: 700,
                fontSize: '0.78rem',
                color: isUser ? 'var(--royal-plum, #54152D)' : 'var(--royal-plum, #54152D)',
                letterSpacing: '0.02em',
              }}
            >
              {isUser ? 'You' : 'Yatra AI'}
            </span>
            {message.created_at && (
              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted, #A39994)' }}>
                {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>

          {/* 1. Markdown Narrative Text */}
          {hasContent && (
            <div data-testid="chat-message-text" style={{ fontSize: '0.96rem', lineHeight: 1.6 }}>
              <MarkdownContent content={message.content} />
            </div>
          )}

          {/* 1.1 Verified Source Attribution & Freshness Indicators */}
          {!isUser && (
            <ProvenanceList message={message} />
          )}

          {/* 1.2 Verified Destination Photograph Gallery (when present) */}
          {!isUser && message.destination_images && message.destination_images.length > 0 && (
            <DestinationGalleryCard
              destination={message.matched_destination}
              images={message.destination_images}
              onExplorePlace={onExplorePlace}
            />
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

          {/* 6b. Interactive Date Picker Card */}
          {(message.intent === 'DATE_CHANGE' || message.showDatePicker) && (
            <InlineDatePickerCard
              initialDeparture={message.request?.start_date || '2026-11-25'}
              initialReturn={message.request?.end_date || '2026-11-28'}
              onSend={onSend}
            />
          )}

          {/* 7. Hotel Mini Card (if single hotel recommendation attached) */}
          {message.hotel && !hasRecommendation && !isBookingHandoff && (
            <HotelMiniCard hotel={message.hotel} />
          )}

          {/* 7b. Alternative Available Hotels Card (if hotel change or alternatives requested) */}
          {message.available_hotels && message.available_hotels.length > 0 && !hasRecommendation && (
            <div
              data-testid="chat-available-hotels-card"
              style={{
                marginTop: '0.75rem',
                background: 'var(--surface-white, #FFFCF9)',
                border: '1px solid var(--border-default, #E9DED6)',
                borderRadius: '12px',
                padding: '12px 14px',
                boxShadow: '0 1px 4px rgba(84, 21, 45, 0.04)',
              }}
            >
              {/* Header with count and top toggle */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '10px',
                  paddingBottom: '8px',
                  borderBottom: '1px solid #F5ECDA',
                  flexWrap: 'wrap',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Building2 size={15} color="var(--royal-plum, #54152D)" />
                  <span style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--burgundy)' }}>
                    Available Katra Accommodations ({message.available_hotels.length})
                  </span>
                </div>
                {message.available_hotels.length > 4 && (
                  <button
                    type="button"
                    onClick={() => setShowAllHotels(!showAllHotels)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--burgundy)',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    <span>{showAllHotels ? 'Show fewer' : `Show all ${message.available_hotels.length}`}</span>
                    {showAllHotels ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                )}
              </div>

              {/* List of hotels */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {(showAllHotels ? message.available_hotels : message.available_hotels.slice(0, 4)).map((h, idx) => {
                  const isLive = Boolean(h.is_live || h.source_provenance === 'LIVE_API' || h.source_provenance === 'LIVE_SERPAPI');
                  const isSmvdsb = h.operator_type === 'SMVDSB' || (h.category && h.category.toUpperCase().includes('DHARAMSHALA'));
                  const priceVal = h.price_per_night != null ? h.price_per_night : (h.price != null ? h.price : null);
                  const priceDisplay = priceVal != null && Number(priceVal) > 0 ? `₹${Number(priceVal).toLocaleString('en-IN')}/night` : 'Tariff on enquiry';

                  return (
                    <div
                      key={h.id || h.property_id || idx}
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid var(--gold-border)',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--burgundy)' }}>
                              {h.name}
                            </span>
                            {isLive ? (
                              <span
                                style={{
                                  fontSize: '0.64rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  background: '#E8F5E9',
                                  color: '#2E7D32',
                                  fontWeight: 600,
                                }}
                              >
                                ⚡ Live Rate
                              </span>
                            ) : isSmvdsb ? (
                              <span
                                style={{
                                  fontSize: '0.64rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  background: 'rgba(212, 175, 55, 0.18)',
                                  color: '#8C6D15',
                                  fontWeight: 600,
                                }}
                              >
                                Official SMVDSB
                              </span>
                            ) : (
                              <span
                                style={{
                                  fontSize: '0.64rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  background: '#F0F0F0',
                                  color: '#555',
                                  fontWeight: 500,
                                }}
                              >
                                Verified Catalog
                              </span>
                            )}
                            {h.category && (
                              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                · {h.category}
                              </span>
                            )}
                          </div>
                          {(h.address || h.location || h.landmark) && (
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {h.landmark ? `${h.landmark} · ` : ''}{h.address || h.location}
                            </div>
                          )}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.84rem', color: 'var(--burgundy)', whiteSpace: 'nowrap' }}>
                            {priceDisplay}
                          </span>
                          <button
                            type="button"
                            onClick={() => onSend && onSend(`Change my hotel to ${h.name}`)}
                            style={{
                              padding: '4px 10px',
                              fontSize: '0.74rem',
                              borderRadius: '6px',
                              background: 'rgba(88, 17, 26, 0.08)',
                              color: 'var(--burgundy)',
                              border: '1px solid var(--gold-border)',
                              cursor: 'pointer',
                              fontWeight: 600,
                            }}
                          >
                            Select
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Bottom toggle button if > 4 */}
              {message.available_hotels.length > 4 && (
                <div style={{ marginTop: '10px', textAlign: 'center' }}>
                  <button
                    type="button"
                    onClick={() => setShowAllHotels(!showAllHotels)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '4px',
                      width: '100%',
                      padding: '7px 12px',
                      background: 'rgba(88, 17, 26, 0.05)',
                      border: '1px dashed var(--gold-border)',
                      borderRadius: '8px',
                      color: 'var(--burgundy)',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <span>
                      {showAllHotels
                        ? `Show fewer (4 of ${message.available_hotels.length})`
                        : `Show all ${message.available_hotels.length} Katra accommodations`}
                    </span>
                    {showAllHotels ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              )}
            </div>
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
        <div style={{ display: 'flex', gap: '8px', marginTop: '4px', paddingLeft: '42px' }}>
          <button
            type="button"
            onClick={() => speakText(message.content)}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '0.72rem',
              color: 'var(--royal-plum, #54152D)',
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
              color: 'var(--text-muted, #A39994)',
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
