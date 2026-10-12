const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness');

test('D5c preserves two time meanings and no published ratio',()=>{
 const raw=fs.readFileSync(path.join(root,'safety.json'));
 const manifest=fs.readFileSync(path.join(root,'safety-manifest.ts'),'utf8');
 assert.ok(manifest.includes(createHash('sha256').update(raw).digest('hex')));
 const data=JSON.parse(raw);
 assert.equal(data.historicalDecision.status,'blocked');
 assert.equal(data.retrospectiveDecision.status,'incomplete');
 assert.equal(data.operatingMargin,null);
 assert.equal(data.publishedMetricCount,0);
 assert.equal(data.filings.length,19);
 assert.equal(data.filings.filter(row=>row.availableAtHistoricalCutoff).length,3);
 assert.equal(data.filings.filter(row=>row.bodyStatus==='retrospective_only').length,16);
 assert.equal(data.filings.filter(row=>row.eventReview==='primary_only_reviewed').length,13);
 assert.equal(data.missingExhibits.length,11);
 assert.equal(data.freshInventory.outsidePinnedWindow.length,2);
 assert.equal(data.profile.known_on,'2026-10-12');
 for(const row of data.filings){assert.ok(row.bodySha256);assert.match(row.url,/^https:\/\/www\.sec\.gov\//);}
 for(const check of data.checks){assert.ok(data.details[check.detailId].sources.length);}
});

test('D5c UI renders the saved evidence without calculating finance',()=>{
 const source=fs.readFileSync(path.join(root,'SafetyReviewPanel.tsx'),'utf8');
 assert.match(source,/data-safety-review/);
 assert.match(source,/Historical application knowledge/);
 assert.match(source,/Retrospective content review/);
 for(const forbidden of ['parseFloat(', 'parseInt(', 'Number(', 'eval(', '/ revenue'])assert.ok(!source.includes(forbidden));
});
