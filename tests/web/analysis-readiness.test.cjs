const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');

const root=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness');

test('D5b readiness artifact has source facts and no published metric',()=>{
 const raw=fs.readFileSync(path.join(root,'snapshot.json'));
 const manifest=fs.readFileSync(path.join(root,'manifest.ts'),'utf8');
 assert.ok(manifest.includes(createHash('sha256').update(raw).digest('hex')));
 const data=JSON.parse(raw);
 assert.equal(data.kind,'real-crcl-analysis-readiness');
 assert.equal(data.sourceInputCount,2);
 assert.equal(data.publishedMetricCount,0);
 assert.deepEqual(data.inputs.map(row=>row.exactValue),['2746642000','-96435000']);
 assert.deepEqual(data.inputs.map(row=>row.displayValue),['$2.75B','−$96.44M']);
 assert.ok(data.inputs.every(row=>row.analysisValue===null));
 assert.ok(data.inputs.every(row=>data.details[row.detailId].sources.length===3));
 assert.equal(data.candidateMetric.value,null);
 assert.equal(data.candidateMetric.displayValue,'N/A');
 assert.deepEqual(data.candidateMetric.reasonCodes,['inventory_history_incomplete','event_history_incomplete']);
});

test('D5b browser component presents supplied values without finance arithmetic',()=>{
 const source=fs.readFileSync(path.join(root,'AnalysisReadinessWorkspace.tsx'),'utf8');
 const error=fs.readFileSync(path.resolve(root,'../../app/development/pilot/analysis/error.tsx'),'utf8');
 assert.match(source,/data-analysis-readiness-kind/);
 assert.match(source,/No ratio has been calculated/);
 assert.match(error,/Retry/);assert.match(error,/window\.location\.reload/);
 for(const forbidden of ['parseFloat(', 'parseInt(', 'Number(', 'eval(', 'operating_income /', '/ revenue']){
  assert.ok(!source.includes(forbidden),`component must not contain ${forbidden}`);
 }
});
