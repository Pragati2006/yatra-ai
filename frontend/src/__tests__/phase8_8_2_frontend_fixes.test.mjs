/**
 * frontend/src/__tests__/phase8_8_2_frontend_fixes.test.mjs
 * Test suite verifying Phase 8.8.2 targeted fixes:
 * 1. Chat streaming URL resolution & fallback
 * 2. Backend PDF retrieval & client-side fallback
 * 3. Base URL resolution across environments
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_PRODUCTION_BACKEND,
  resolveApiConfig,
  getApiBaseUrl,
  streamChat,
} from '../services/api.js';

import {
  downloadPilgrimPassPDF,
} from '../utils/pdfGenerator.js';

describe('Phase 8.8.2: Base URL & Chat Streaming URL Resolution', () => {
  it('1. Production mode with VITE_API_URL unset defaults to DEFAULT_PRODUCTION_BACKEND', () => {
    const config = resolveApiConfig('', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, false);
    assert.equal(config.baseUrl, DEFAULT_PRODUCTION_BACKEND);
    assert.equal(config.baseUrl, 'https://yatra-ai-smap.onrender.com');
  });

  it('2. Production mode with explicit approved onrender.com URL succeeds', () => {
    const config = resolveApiConfig('https://my-backend-instance.onrender.com/', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, false);
    assert.equal(config.baseUrl, 'https://my-backend-instance.onrender.com');
  });

  it('3. Production mode with explicit trycloudflare.com tunnel succeeds', () => {
    const config = resolveApiConfig('https://secure-gate-77.trycloudflare.com', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, false);
    assert.equal(config.baseUrl, 'https://secure-gate-77.trycloudflare.com');
  });

  it('4. Development mode defaults to http://127.0.0.1:8000 when unset', () => {
    const config = resolveApiConfig('', { isDev: true, isProd: false });
    assert.equal(config.isMisconfigured, false);
    assert.equal(config.baseUrl, 'http://127.0.0.1:8000');
  });

  it('5. Production mode strictly rejects insecure HTTP URLs', () => {
    const config = resolveApiConfig('http://yatra-ai-smap.onrender.com', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, true);
    assert.match(config.errorMessage, /Insecure backend URL rejected in production/);
  });

  it('6. Production mode strictly rejects arbitrary unapproved external domains', () => {
    const config = resolveApiConfig('https://evil-spoof.attacker.org', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, true);
    assert.match(config.errorMessage, /Untrusted backend origin rejected/);
  });

  it('7. Rejects credential-bearing URLs for security', () => {
    const config = resolveApiConfig('https://user:password@yatra-ai-smap.onrender.com', { isDev: false, isProd: true });
    assert.equal(config.isMisconfigured, true);
    assert.match(config.errorMessage, /Credential-bearing API URLs are rejected/);
  });

  it('8. getApiBaseUrl() returns valid production origin or local dev origin', () => {
    const currentBase = getApiBaseUrl();
    assert.ok(currentBase && typeof currentBase === 'string');
    assert.ok(currentBase.startsWith('http://') || currentBase.startsWith('https://'));
  });

  it('9. streamChat() properly constructs the streaming endpoint with resolved baseURL', async () => {
    let requestedUrl = null;
    let requestOptions = null;

    // Mock global fetch to inspect endpoint invocation
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (url, opts) => {
        requestedUrl = url;
        requestOptions = opts;
        // Mock SSE response stream
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"type": "start"}\n\n'));
            controller.enqueue(encoder.encode('data: {"type": "token", "content": "Jai Mata Di!"}\n\n'));
            controller.enqueue(encoder.encode('data: {"type": "done", "response": {"reply": "Jai Mata Di!"}}\n\n'));
            controller.close();
          },
        });
        return new Response(stream, {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
        });
      };

      const tokens = [];
      const res = await streamChat(
        { message: 'Jai Mata Di', session_id: 'test-session-123' },
        {
          onToken: (tok) => tokens.push(tok),
        }
      );

      assert.ok(requestedUrl, 'Fetch must have been called');
      assert.ok(requestedUrl.endsWith('/api/chat/stream'), `Expected /api/chat/stream, got ${requestedUrl}`);
      assert.ok(!requestedUrl.startsWith('//'), 'URL must not contain duplicate leading slashes');
      assert.equal(requestOptions.method, 'POST');
      assert.equal(tokens.join(''), 'Jai Mata Di!');
      assert.equal(res?.reply, 'Jai Mata Di!');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('10. streamChat() cleanly invokes onError and throws when backend stream fails', async () => {
    const originalFetch = globalThis.fetch;
    let errorReceived = null;
    try {
      globalThis.fetch = async () => {
        return new Response('Internal Server Error', { status: 500 });
      };

      await assert.rejects(
        async () => {
          await streamChat(
            { message: 'Test Fail', session_id: 'test-session-err' },
            {
              onError: (err) => {
                errorReceived = err;
              },
            }
          );
        },
        /Streaming failed: HTTP 500/
      );

      assert.ok(errorReceived, 'onError callback must have received the failure');
      assert.match(errorReceived.message, /Streaming failed: HTTP 500/);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});

describe('Phase 8.8.2: Backend PDF Integration & Client-Side Fallback', () => {
  const dummyBooking = {
    booking_id: 'VD-TEST-9999',
    user_name: 'Shri Pilgrim Devotee',
    pax_count: 2,
    slot_date: '2026-10-20',
    category: 'Normal Darshan',
    slot_time: 'Morning Slot (06:00)',
    total_price: 12000,
  };

  const dummySummary = {
    origin: 'Delhi',
    option: {
      transport: { name: 'Vande Bharat Express', mode: 'Train' },
      slot: { category: 'Normal Darshan', slot_date: '2026-10-20', slot_time: 'Morning Slot (06:00)' },
    },
    hotel: { name: 'Hotel Asia Vaishno Devi' },
    pax: 2,
    total_price: 12000,
  };

  it('1. Backend PDF success: downloads authentic PDF bytes from backend', async () => {
    // Mock backend PDF returning valid %PDF-1.4 blob
    const pdfBytes = new TextEncoder().encode('%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF');
    const mockBlob = new Blob([pdfBytes], { type: 'application/pdf' });

    let fetchCalledWith = null;
    const mockFetchPdf = async (bid) => {
      fetchCalledWith = bid;
      return mockBlob;
    };

    const res = await downloadPilgrimPassPDF(dummyBooking, dummySummary, { fetchPdf: mockFetchPdf });
    assert.equal(fetchCalledWith, 'VD-TEST-9999');
    assert.equal(res.source, 'backend');
    assert.equal(res.success, true);
  });

  it('2. Backend PDF 401 Unauthorized: gracefully falls back to client-side generator', async () => {
    const mockFetchPdf = async () => {
      const err = new Error('Request failed with status code 401');
      err.response = { status: 401, data: { detail: 'Authentication required to download booking pass. Please sign in.' } };
      throw err;
    };

    const res = await downloadPilgrimPassPDF(dummyBooking, dummySummary, { fetchPdf: mockFetchPdf });
    assert.equal(res.source, 'client');
    assert.equal(res.success, true);
  });

  it('3. Backend PDF 404 Not Found: gracefully falls back to client-side generator', async () => {
    const mockFetchPdf = async () => {
      const err = new Error('Request failed with status code 404');
      err.response = { status: 404, data: { detail: 'Booking record not found or access denied for this account.' } };
      throw err;
    };

    const res = await downloadPilgrimPassPDF(dummyBooking, dummySummary, { fetchPdf: mockFetchPdf });
    assert.equal(res.source, 'client');
    assert.equal(res.success, true);
  });

  it('4. Backend PDF Server 500 error: gracefully falls back to client-side generator', async () => {
    const mockFetchPdf = async () => {
      throw new Error('500 Internal Server Error');
    };

    const res = await downloadPilgrimPassPDF(dummyBooking, dummySummary, { fetchPdf: mockFetchPdf });
    assert.equal(res.source, 'client');
    assert.equal(res.success, true);
  });

  it('5. Backend PDF invalid/corrupted response (e.g. JSON error as 200 or empty): falls back to client generator', async () => {
    // Non-PDF blob (HTML/JSON or too small)
    const invalidBlob = new Blob(['{"error": "something"}'], { type: 'application/json' });
    const mockFetchPdf = async () => invalidBlob;

    const res = await downloadPilgrimPassPDF(dummyBooking, dummySummary, { fetchPdf: mockFetchPdf });
    assert.equal(res.source, 'client');
    assert.equal(res.success, true);
  });

  it('6. Missing booking_id / guest mode without fetcher: uses client generator', async () => {
    const res = await downloadPilgrimPassPDF({}, dummySummary);
    assert.equal(res.source, 'client');
    assert.equal(res.success, true);
  });
});
