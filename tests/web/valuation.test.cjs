const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

function loadPresentation() {
  const source = fs.readFileSync(path.resolve(__dirname, '../../apps/web/src/features/valuation/presentation.ts'), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
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

const examples = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../apps/web/src/features/valuation/fixture.json'), 'utf8')).examples;
const reference = examples.find(row => row.id === 'reference').payload;
test('scenario span eligibility reports each saved null-span state', () => {
  assert.deepEqual(presentation.spanStatus(reference), { eligible: true, label: 'Complete eligible named roster' });
  const expected = {
    no_solution_in_domain: 'reference: No solution in domain; at least two named scenarios required',
    inconclusive: 'reference: Inconclusive; at least two named scenarios required',
    unavailable: 'low investment: Unavailable; reference: Unavailable; high investment: Unavailable',
    non_unique: 'reference: Multiple solutions; at least two named scenarios required',
    missing: 'Missing saved result',
  };
  for (const example of examples.filter(row => row.id !== 'reference')) {
    assert.deepEqual(presentation.spanStatus(example.payload), { eligible: false, label: expected[example.id] });
  }
});
test('scenario span never calls an absent or incomplete roster eligible', () => {
  const single = structuredClone(reference);
  single.scenarios = [single.scenarios[1]];
  single.assumptions.scenarios = [single.assumptions.scenarios[1]];
  assert.equal(presentation.spanStatus(single).eligible, false);
  assert.equal(presentation.spanStatus(single).label, 'at least two named scenarios required');
  const missing = structuredClone(reference); missing.scenario_dispersion = null;
  assert.equal(presentation.spanStatus(missing).label, 'Saved scenario span unavailable');
  const noScalar = structuredClone(reference); noScalar.scenarios[0].solve.representative = null;
  assert.equal(presentation.spanStatus(noScalar).eligible, false);
  const unnamed = structuredClone(reference); unnamed.scenarios[0].name = '';
  assert.equal(presentation.spanStatus(unnamed).eligible, false);
});
test('bridge endpoints preserve the saved exact strings and signed amounts', () => {
  const payload = structuredClone(reference);
  const scenario = payload.scenarios[1];
  Object.assign(scenario.evaluation, { operating_ev: '-9.00000000000000000001' });
  scenario.common_equity = '-29.00000000000000000001';
  scenario.conditional_per_share = '-2.900000000000000000001';
  assert.deepEqual(presentation.bridgeEndpoints(payload, scenario).map(row => row.value), [
    '-9.00000000000000000001', '-20', '-29.00000000000000000001', '10', '-2.900000000000000000001',
  ]);
  for (const example of examples.filter(row => row.payload && row.id !== 'reference')) {
    const rows = presentation.bridgeEndpoints(example.payload, example.payload.scenarios[0]);
    assert.equal(rows[0].value, null);
    assert.equal(rows[2].value, null);
    assert.equal(rows[4].value, null);
  }
});
test('complete span requires exactly the declared scenario roster', () => {
  const incomplete = structuredClone(reference); incomplete.scenarios.pop();
  assert.deepEqual(presentation.spanStatus(incomplete), { eligible: false, label: 'Declared scenario roster is incomplete or duplicated' });
  const duplicate = structuredClone(reference); duplicate.scenarios[2] = duplicate.scenarios[0];
  assert.equal(presentation.spanStatus(duplicate).eligible, false);
  const unknown = structuredClone(reference); unknown.scenarios[2].name = 'undeclared';
  assert.equal(presentation.spanStatus(unknown).eligible, false);
});

// Display-only rounding oracles; saved Decimal evidence must not be rewritten.
test('rounds decimal strings half away from zero without binary precision loss', () => {
  for (const [input, expected] of [
    ['17.34375', '17.3438'], ['-17.34375', '-17.3438'],
    ['1.234449999999999999999', '1.2344'], ['1.23445', '1.2345'],
    ['9.99995', '10'], ['-0.000049', '0'], ['-0.00005', '-0.0001'],
    ['0.00005', '0.0001'], ['1.23000000000000000', '1.23'],
    ['9007199254740993.12345', '9007199254740993.1235'],
    ['9007199254740993', '9007199254740993'], ['1.23456E-2', '0.0123'],
    ['1E-80', '0'], ['1.23455e+2', '123.455'], ['+1.23456', '+1.2346'],
  ]) assert.equal(presentation.rounded(input), expected, input);
  assert.equal(presentation.number('9007199254740993.12345'), '9,007,199,254,740,993.1235');
  assert.equal(presentation.number('0.1234565', true), '12.3457%');
  assert.equal(presentation.number('-0.0000001', true), '0%');
  assert.equal(presentation.rounded(null), 'N/A');
  assert.equal(presentation.rounded(0), '0');
  assert.equal(presentation.rounded(-1.23456), '-1.2346');
});
test('structured display rounds only numeric fields and preserves all exact evidence', () => {
  const value = { lower: '0.123456789', upper: '-1.23455',
    proof: [{ residual: { lower: '1E-50', upper: '0.000056' } }],
    taxes: ['0.123456'], name: '1.234567', variable: 'terminal_operating_margin',
    id: '12345678901234567890', source_id: '1.234567', hash: '123e10',
    evidence_hash: '9'.repeat(64), authored_at: '2026-09-29T00:00:00Z',
    reasons: ['0.123456'], metadata: { lower: '1.234567' } };
  const saved = JSON.stringify(value);
  assert.deepEqual(JSON.parse(presentation.rounded(value)), { ...value,
    lower: '0.1235', upper: '-1.2346',
    proof: [{ residual: { lower: '0', upper: '0.0001' } }], taxes: ['0.1235'] });
  assert.equal(JSON.stringify(value), saved);
  assert.equal(presentation.exact(value), JSON.stringify(value, null, 2));
  for (const raw of ['2026-09-29', '2026-09-29T00:00:00Z', 'abc123e10', '001234', 'N/A', '', ' 1.23456 ', '123-456', 'NaN', 'Infinity']) {
    assert.equal(presentation.rounded(raw), raw);
  }
  assert.equal(presentation.exact('17.343750000000000000'), '17.343750000000000000');
});
