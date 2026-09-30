const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../../apps/web/src/features/normalization');
test('D5a checked real projection has exact values, separate modes and evidence',()=>{
 const raw=fs.readFileSync(path.join(root,'snapshot.json'));
 const manifest=fs.readFileSync(path.join(root,'manifest.ts'),'utf8');
 assert.ok(manifest.includes(createHash('sha256').update(raw).digest('hex')));
 const data=JSON.parse(raw);assert.equal(data.kind,'real-crcl-normalization');
 assert.deepEqual(data.views.as_filed.facts.map(row=>row.value),['2746642000','-96435000']);
 assert.ok(data.views.before_filing.facts.every(row=>row.value===null));
 for(const view of Object.values(data.views))for(const fact of view.facts){
  assert.ok(data.details[fact.detailId]);
  assert.ok(data.details[fact.detailId].sources.every(source=>new URL(source.url).hostname.endsWith('.sec.gov')));
 }
 assert.equal(data.factCount,2);assert.equal(data.captureCount,5);
});
