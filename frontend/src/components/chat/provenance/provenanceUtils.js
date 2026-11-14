import React from 'react';
import { AlertTriangle, FlaskConical, X, Landmark, Info } from 'lucide-react';

/**
 * frontend/src/components/chat/provenance/provenanceUtils.js
 * Comprehensive normalization, formatting, and security utilities for
 * Yatra AI frontend source attribution and data freshness indicators.
 */

export const SOURCE_TYPE_LABELS = {
  live_api: 'Live data',
  cached_api: 'Cached data',
  static_rag: 'Knowledge base',
  curated_data: 'Curated information',
  indicative_data: 'Indicative information',
  simulated_data: 'Simulated demonstration',
  unknown_source: 'Source not verified',
};

export const FRESHNESS_LABELS = {
  live: 'Live data',
  cached: 'Cached data',
  stale: 'Potentially outdated',
  fallback: 'Fallback estimate',
  simulated: 'Simulated demonstration',
  unavailable: 'Currently unavailable',
  not_applicable: 'Static / Curated',
};

export const VERIFICATION_LABELS = {
  verified_external_api: 'Verified External API',
  verified_official_source: 'Verified Official Source',
  verified_curated_source: 'Verified Curated Source',
  verified_internal_knowledge: 'Verified Internal Knowledge',
  partially_verified: 'Partially Verified',
  indicative_information: 'Indicative Information',
  simulation_only: 'Simulation Only',
  unverified: 'Unverified',
  not_applicable: 'N/A',
};

/**
 * Maps backend source_type and freshness_status into a clear, honest user-facing label.
 * Strictly adheres to truth-in-data guidelines:
 * - Cached is never displayed as live.
 * - Static RAG is never displayed as live.
 * - Simulated data is never displayed as official/confirmed.
 */
export function getEffectiveSourceLabel(source) {
  if (!source || typeof source !== 'object') {
    return 'Source not verified';
  }

  const sType = (source.source_type || '').toLowerCase();
  const fresh = (source.freshness_status || '').toLowerCase();

  if (fresh === 'stale') {
    return 'Potentially outdated';
  }
  if (fresh === 'unavailable') {
    return 'Currently unavailable';
  }
  if (fresh === 'fallback') {
    return 'Fallback estimate';
  }
  if (sType === 'live_api' && fresh === 'live') {
    return 'Live data';
  }
  if (fresh === 'cached' || sType === 'cached_api') {
    return 'Cached data';
  }
  if (sType === 'static_rag') {
    return 'Knowledge base';
  }
  if (sType === 'curated_data') {
    return 'Curated information';
  }
  if (sType === 'indicative_data') {
    return 'Indicative information';
  }
  if (sType === 'simulated_data' || fresh === 'simulated') {
    return 'Simulated demonstration';
  }
  if (fresh === 'unavailable') {
    return 'Currently unavailable';
  }

  return SOURCE_TYPE_LABELS[sType] || 'Source not verified';
}

/**
 * Returns accessible visual design tokens for a given freshness state.
 */
export function getFreshnessStyle(freshness, sourceType) {
  const fresh = (freshness || '').toLowerCase();
  const sType = (sourceType || '').toLowerCase();

  if (fresh === 'stale') {
    return {
      bg: '#FFF8E6',
      color: '#8A5D00',
      border: '#FAD980',
      icon: React.createElement(AlertTriangle, { size: 11 }),
      label: 'Potentially outdated',
      ariaLabel: 'Potentially outdated information',
    };
  }

  if (fresh === 'live' && sType === 'live_api') {
    return {
      bg: '#EBFBF2',
      color: '#147A44',
      border: '#A6E9C1',
      icon: '●',
      label: 'Live',
      ariaLabel: 'Live external information',
    };
  }

  if (fresh === 'cached' || sType === 'cached_api') {
    return {
      bg: '#F0F5FF',
      color: '#1B4D8A',
      border: '#BAD3F7',
      icon: '○',
      label: 'Cached',
      ariaLabel: 'Cached information retrieved earlier',
    };
  }

  if (fresh === 'fallback') {
    return {
      bg: '#FFF3E8',
      color: '#A04A00',
      border: '#F5C69C',
      icon: '≈',
      label: 'Fallback estimate',
      ariaLabel: 'Fallback estimate',
    };
  }

  if (fresh === 'simulated' || sType === 'simulated_data') {
    return {
      bg: '#F7F0FF',
      color: '#5B2C91',
      border: '#DEC7FF',
      icon: React.createElement(FlaskConical, { size: 11 }),
      label: 'Simulated',
      ariaLabel: 'Simulated demonstration environment',
    };
  }

  if (fresh === 'unavailable') {
    return {
      bg: '#FFF0F0',
      color: '#A91B1B',
      border: '#F7C2C2',
      icon: React.createElement(X, { size: 11 }),
      label: 'Unavailable',
      ariaLabel: 'Information currently unavailable',
    };
  }

  if (sType === 'static_rag') {
    return {
      bg: '#FAF6F0',
      color: '#58111A',
      border: '#E5D2AD',
      icon: React.createElement(Landmark, { size: 11 }),
      label: 'Knowledge base',
      ariaLabel: 'Static verified knowledge base',
    };
  }

  return {
    bg: '#F8F9FA',
    color: '#495057',
    border: '#CED4DA',
    icon: React.createElement(Info, { size: 11 }),
    label: 'Standard',
    ariaLabel: 'Information source',
  };
}

/**
 * Formats a timezone-aware ISO 8601 string into a readable local date and time.
 * Handles UTC (Z, +00:00) and offset-aware strings safely.
 * Returns null for missing, empty, or invalid timestamps.
 * NEVER defaults to current time.
 */
export function formatTimestamp(isoString) {
  if (!isoString || typeof isoString !== 'string') {
    return null;
  }
  const trimmed = isoString.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Date.parse(trimmed);
  if (isNaN(parsed)) {
    return null;
  }

  try {
    const d = new Date(parsed);
    return d.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return null;
  }
}

/**
 * Validates external URLs to prevent XSS and malicious redirects.
 * Strictly permits only http: and https: protocols.
 * Rejects javascript:, data:, vbscript:, and malformed strings.
 */
export function sanitizeUrl(url) {
  if (!url || typeof url !== 'string') {
    return null;
  }
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.href;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Normalizes and extracts safe provenance records from an AI message.
 * Excludes failed and timed-out tools from being displayed as successful sources.
 * Integrates legacy knowledge_sources if modern source_provenance is empty.
 */
export function extractValidProvenance(message) {
  if (!message || typeof message !== 'object') {
    return [];
  }

  const rawList = message.source_provenance || message.data_provenance || [];
  const validRecords = [];
  const seenKeys = new Set();

  if (Array.isArray(rawList)) {
    for (const item of rawList) {
      if (!item || typeof item !== 'object') continue;

      // Filter out failed or timed out executions falsely passed as sources
      const fresh = (item.freshness_status || '').toLowerCase();
      if (fresh === 'failed' || fresh === 'timeout' || fresh === 'invalid_tool_response') {
        continue;
      }

      const name = (item.source_name || item.name || '').trim();
      const sType = (item.source_type || '').toLowerCase();
      const loc = (item.location || '').toLowerCase();
      const dedupKey = `${name}:${sType}:${loc}`;

      if (name && !seenKeys.has(dedupKey)) {
        seenKeys.add(dedupKey);
        validRecords.push(item);
      }
    }
  }

  // Fallback: Check knowledge_sources array (e.g. from static RAG)
  if (validRecords.length === 0 && Array.isArray(message.knowledge_sources)) {
    for (const ks of message.knowledge_sources) {
      if (!ks || typeof ks !== 'object') continue;
      const name = ks.source_name || ks.title || 'Vaishno Devi Knowledge Base';
      const dedupKey = `${name}:static_rag:`;
      if (!seenKeys.has(dedupKey)) {
        seenKeys.add(dedupKey);
        validRecords.push({
          source_name: name,
          source_type: 'static_rag',
          freshness_status: 'not_applicable',
          verification_status: 'verified_curated_source',
          source_url: ks.source_url || null,
          retrieval_timestamp: ks.last_verified || null,
          domain: ks.domain || 'pilgrimage',
          disclaimer: ks.disclaimer || null,
        });
      }
    }
  }

  return validRecords;
}
