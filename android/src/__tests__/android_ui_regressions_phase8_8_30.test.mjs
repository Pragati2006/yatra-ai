import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const androidRoot = path.resolve(__dirname, '../..');
const repoRoot = path.resolve(androidRoot, '..');

test('Regression 1: All navigation restored in Sidebar Drawer with CHAT & YATRA SERVICES', () => {
  const drawerFile = path.join(androidRoot, 'src/components/SidebarDrawer.jsx');
  const code = fs.readFileSync(drawerFile, 'utf-8');

  // CHAT Group
  assert.ok(code.includes('New Chat'), 'Must include New Chat');
  assert.ok(code.includes('Search conversations...'), 'Must include conversation search');
  assert.ok(code.includes('RECENT CONVERSATIONS'), 'Must include chat history/recent conversations');

  // YATRA SERVICES Group
  assert.ok(code.includes('YATRA SERVICES'), 'Must include YATRA SERVICES section header');
  assert.ok(code.includes("onNavigate('Assistant')"), 'Must navigate to Assistant');
  assert.ok(code.includes("onNavigate('Booking')"), 'Must navigate to Booking');
  assert.ok(code.includes("onNavigate('Stay')"), 'Must navigate to Stay / Accommodation');
  assert.ok(code.includes("onNavigate('Transport')"), 'Must navigate to Transport');
  assert.ok(code.includes("onNavigate('Destinations')"), 'Must navigate to Destinations');
  assert.ok(code.includes("onNavigate('Weather')"), 'Must navigate to Weather');

  // Active state support
  assert.ok(code.includes('activeRoute'), 'Must accept activeRoute prop');
  assert.ok(code.includes('navItemActive'), 'Must define navItemActive styling');
  assert.ok(code.includes('activeIndicator'), 'Must render activeIndicator dot');
});

test('Regression 2: Keyboard handling and message composer visibility', () => {
  const chatFile = path.join(androidRoot, 'src/screens/ChatScreen.jsx');
  const chatCode = fs.readFileSync(chatFile, 'utf-8');

  assert.ok(chatCode.includes('Keyboard'), 'ChatScreen must import Keyboard');
  assert.ok(chatCode.includes('keyboardDidShow'), 'ChatScreen must listen for keyboard show event');
  assert.ok(chatCode.includes('scrollToEnd'), 'ChatScreen must scroll to end when keyboard opens');

  const composerFile = path.join(androidRoot, 'src/components/MessageComposer.jsx');
  const composerCode = fs.readFileSync(composerFile, 'utf-8');
  assert.ok(composerCode.includes('multiline'), 'MessageComposer must support multiline input');
  assert.ok(composerCode.includes('maxHeight: 120'), 'MessageComposer input must expand up to maxHeight 120');
  assert.ok(composerCode.includes('alignItems: \'flex-end\''), 'MessageComposer must anchor send button at bottom');
});

test('Regression 3: Parimal alias in backend agents', () => {
  const knowledgeFile = path.join(repoRoot, 'agents/knowledge_agent.py');
  const knowledgeCode = fs.readFileSync(knowledgeFile, 'utf-8');
  assert.ok(knowledgeCode.includes('"parimal": "Pari Mahal"'), 'knowledge_agent must map parimal to Pari Mahal');

  const itineraryFile = path.join(repoRoot, 'agents/itinerary_agent.py');
  const itineraryCode = fs.readFileSync(itineraryFile, 'utf-8');
  assert.ok(itineraryCode.includes('"parimal": "Pari Mahal"'), 'itinerary_agent must map parimal to Pari Mahal');

  const conversationFile = path.join(repoRoot, 'agents/conversation_agent.py');
  const conversationCode = fs.readFileSync(conversationFile, 'utf-8');
  assert.ok(conversationCode.includes('parimal'), 'conversation_agent regex must include parimal');
});

test('Regression 4: Markdown headings level 1-6 and inline delimiters __ and _', async () => {
  const parserModule = await import('../utils/markdownParser.js');
  const parseMarkdownStructure = parserModule.parseMarkdownStructure;

  const testMd = [
    '# H1 Title',
    '## H2 Title',
    '### H3 Title',
    '#### H4 Title',
    '##### H5 Title',
    '###### H6 Title',
    '- Dash bullet',
    '* Star bullet',
    '• Unicode bullet',
    '+ Plus bullet',
    '1. Dot number',
    '2) Paren number',
  ].join('\n');

  const blocks = parseMarkdownStructure(testMd);
  assert.equal(blocks.length, 12);
  assert.equal(blocks[0].level, 1);
  assert.equal(blocks[1].level, 2);
  assert.equal(blocks[2].level, 3);
  assert.equal(blocks[3].level, 4);
  assert.equal(blocks[4].level, 5);
  assert.equal(blocks[5].level, 6);

  assert.equal(blocks[6].type, 'bullet');
  assert.equal(blocks[7].type, 'bullet');
  assert.equal(blocks[8].type, 'bullet');
  assert.equal(blocks[9].type, 'bullet');

  assert.equal(blocks[10].type, 'numbered');
  assert.equal(blocks[11].type, 'numbered');

  // Verify MarkdownView inline regex covers __bold__ and _italic_
  const markdownViewFile = path.join(androidRoot, 'src/components/MarkdownView.jsx');
  const viewCode = fs.readFileSync(markdownViewFile, 'utf-8');
  assert.ok(viewCode.includes('__[^_]+__'), 'renderInlineSpans must match __bold__');
  assert.ok(viewCode.includes('_[^_]+_'), 'renderInlineSpans must match _italic_');
});

test('Regression 5: Header vertical spacing and alignment', () => {
  const headerFile = path.join(androidRoot, 'src/components/Header.jsx');
  const headerCode = fs.readFileSync(headerFile, 'utf-8');

  assert.ok(headerCode.includes('translucent={false}'), 'Header must set translucent={false} on Android');
  assert.ok(headerCode.includes('Platform.OS === \'android\' ? 6 : Math.max(insets.top, 8)'), 'Header must apply clean top padding without awkward void');
  assert.ok(headerCode.includes('justifyContent: \'center\''), 'Header titleContainer must vertically center');
  assert.ok(headerCode.includes('minHeight: 40'), 'Header topRow must specify unified vertical alignment minHeight');
});

