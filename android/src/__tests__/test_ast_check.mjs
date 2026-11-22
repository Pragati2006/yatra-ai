import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

const babelParser = require('@babel/parser');
const babelTraverse = require('@babel/traverse').default || require('@babel/traverse');

const srcDir = path.resolve(__dirname, '..');
console.log('Inspecting JSX/JS files in:', srcDir);

const files = [];
function findFiles(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== '__tests__') findFiles(full);
    } else if (full.endsWith('.jsx') || full.endsWith('.js')) {
      files.push(full);
    }
  }
}
findFiles(srcDir);

const KNOWN_GLOBALS = new Set([
  'console', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
  'fetch', 'Headers', 'Request', 'Response', 'FormData', 'URL', 'URLSearchParams',
  'Promise', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Array', 'Object', 'String', 'Number',
  'Boolean', 'Date', 'RegExp', 'Error', 'TypeError', 'RangeError', 'ReferenceError',
  'SyntaxError', 'JSON', 'Math', 'parseInt', 'parseFloat', 'isNaN', 'isFinite',
  'decodeURI', 'decodeURIComponent', 'encodeURI', 'encodeURIComponent',
  'window', 'global', 'globalThis', '__DEV__', 'process', 'module', 'exports',
  'require', 'Intl', 'Buffer', 'NaN', 'undefined', 'Infinity', 'navigator', 'alert', 'AbortController'
]);

let issuesFound = 0;

for (const f of files) {
  const code = fs.readFileSync(f, 'utf-8');
  try {
    const ast = babelParser.parse(code, {
      sourceType: 'module',
      plugins: ['jsx']
    });
    
    const undeclared = new Set();
    babelTraverse(ast, {
      Identifier(p) {
        if (p.isReferencedIdentifier()) {
          const name = p.node.name;
          if (!KNOWN_GLOBALS.has(name) && !p.scope.hasBinding(name)) {
            undeclared.add(name);
          }
        }
      }
    });

    if (undeclared.size > 0) {
      issuesFound++;
      console.log(`[UNDECLARED in ${path.relative(srcDir, f)}]:`, Array.from(undeclared));
    }
  } catch (err) {
    console.log(`[PARSE ERROR in ${path.relative(srcDir, f)}]:`, err.message);
  }
}

console.log(`AST Scan completed. Total files with undeclared identifiers: ${issuesFound}`);
