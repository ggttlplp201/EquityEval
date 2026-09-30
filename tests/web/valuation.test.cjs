const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

function loadPresentation() {
  const source = fs.readFileSync(path.resolve(__dirname, '../../apps/web/src/features/valuation/presentation.ts'), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
  const module = { exports: {} };
  new Function('module', 'exports', js)(module, module.exports);
  return module.exports;
}
const presentation = loadPresentation();
test('missing stays N/A while real zero and signed values render', () => {
  assert.equal(presentation.number(null), 'N/A');
  assert.equal(presentation.number(undefined), 'N/A');
  assert.equal(presentation.number('0'), '0');
  assert.equal(presentation.number('-20'), '-20');
  assert.equal(presentation.number('.2', true), '20%');
  assert.equal(presentation.exact('0.20000000000000000001'), '0.20000000000000000001');
});
test('all solver states retain distinct presentation labels', () => {
  assert.equal(new Set(Object.values(presentation.states)).size, 5);
  assert.equal(presentation.states.non_unique, 'Multiple solutions');
  assert.equal(presentation.states.inconclusive, 'Inconclusive');
  assert.equal(presentation.interval(null), 'N/A');
});
