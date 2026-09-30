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

test('D5a PIT evidence excludes review-only and later-filing material',()=>{
 const data=JSON.parse(fs.readFileSync(path.join(root,'snapshot.json')));
 for(const mode of ['as_filed','original'])for(const fact of data.views[mode].facts){
  const detail=data.details[fact.detailId];assert.equal(detail.sources.length,3);assert.equal(detail.reviewContext.length,2);
  assert.deepEqual(detail.reviewContext.map(item=>item.accession),['0001876042-26-000228','0001876042-26-000248']);
 }
 for(const fact of data.views.before_filing.facts){
  const detail=data.details[fact.detailId];assert.deepEqual(detail.sources,[]);assert.deepEqual(detail.reviewContext,[]);
  for(const future of ['2,746,642','96,435','2746642000','96435000','Original literal','Scale','Decimals','c-1'])assert.ok(!JSON.stringify(detail).includes(future));
 }
});
