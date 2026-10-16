const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness');

test('D5k keeps annual and instant scopes, provenance and unsupported slots separate',()=>{
 const raw=fs.readFileSync(path.join(root,'broader.json'));
 assert.ok(fs.readFileSync(path.join(root,'broader-manifest.ts'),'utf8').includes(createHash('sha256').update(raw).digest('hex')));
 const data=JSON.parse(raw);
 assert.equal(data.sourceObservation,'2026-10-15T21:59:05.195192+00:00');
 assert.equal(data.bodyCount,41);assert.equal(data.comparisonCount,101);
 for(const result of data.results){
  const count=result.basis==='annual'?4:2;
  assert.equal(result.metrics.length,count);assert.equal(result.gaps.length,10-count);
  assert.equal(result.snapshot.result.coverage.counts.valid,count);
  assert.equal(result.snapshot.result.coverage.counts.invalid,0);
  for(const item of [...result.metrics,...result.operands])assert.ok(data.details[item.id].sources.length);
  assert.ok(data.details[result.accountingDetail].sources.length);
 }
 assert.equal(data.comparativeRows.length,8);
 for(const row of data.comparativeRows){assert.ok(data.details[row.id].sources.length);assert.match(data.details[row.id].subtitle,/not an eligible/);}
 assert.equal(data.missingHistory.length,9);
 assert.equal(data.missingHistory.filter(r=>r.resourceKey.endsWith('.pdf')).length,4);
});

test('D5k renders supplied values without frontend finance calculations',()=>{
 const source=fs.readFileSync(path.join(root,'BroaderFundamentalsPanel.tsx'),'utf8');
 for(const forbidden of ['parseFloat(', 'parseInt(', 'Number(', 'eval('])assert.ok(!source.includes(forbidden));
 assert.match(source,/not available corporate liquidity|freely available corporate liquidity/);
 assert.match(source,/not complete analysis history/);
});
