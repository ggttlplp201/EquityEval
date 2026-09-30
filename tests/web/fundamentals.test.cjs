const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
function load(file) {
  const source=fs.readFileSync(path.resolve(__dirname, '../../apps/web/src/features', file), 'utf8');
  const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const module={exports:{}};
  new Function('module','exports','require',js)(module,module.exports,()=>load('valuation/presentation.ts'));
  return module.exports;
}
const p=load('fundamentals/presentation.ts');
test('all seven statuses and saved values remain distinct',()=>{
  assert.equal(Object.keys(p.statuses).length,7);
  assert.equal(new Set(Object.values(p.statuses)).size,7);
  assert.equal(p.metricDisplay({status:'not_meaningful',value:null,unit:'multiple'}),'N/M');
  assert.equal(p.metricDisplay({status:'missing',value:null,unit:'USD'}),'N/A');
  assert.equal(p.metricDisplay({status:'valid',value:'0',unit:'USD'}),'0');
  assert.equal(p.metricDisplay({status:'stale',value:'-0.1234565',unit:'fraction'}),'-12.3457%');
  assert.equal(p.metricDisplay({status:'inapplicable',value:'1.234567',unit:'multiple'}),'1.2346×');
});
test('required ordered sections and bounded saved notes',()=>{
  assert.deepEqual(p.sections.map(s=>s.title),['Growth','Profitability','Cash generation','Balance sheet','Valuation','Returns on capital']);
  const review=[0,1,2,3].map(n=>({topic:String(n),text:'saved '+n}));
  assert.deepEqual(p.savedNotes({review_items:review,observations:[review[0]]}),review.slice(0,3));
});
test('all generated metrics have exactly one declared presentation section',()=>{
  const bundle=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../apps/web/src/features/fundamentals/fixture.json'),'utf8'));
  for(const row of bundle.snapshots)for(const metric of row.payload.metrics){
    assert.ok(p.metrics[metric.metric_id]);
    assert.equal(p.sections.filter(s=>s.ids.includes(metric.metric_id)).length,1);
  }
});

test('tied quartile coordinates use one readable combined label',()=>{
  assert.deepEqual(p.chartLabels(['50','50','50']),[{x:'50',label:'P25 = Median = P75'}]);
  assert.deepEqual(p.chartLabels(['10','10','90']),[{x:'10',label:'P25 = Median'},{x:'90',label:'P75'}]);
});
const selection=load('fundamentals/selection.ts');
test('saved route fails closed for unknown keys and ambiguous examples or snapshots',()=>{
  const bundle=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../apps/web/src/features/fundamentals/fixture.json'),'utf8'));
  assert.equal(selection.resolveSelection(bundle,{yeas:'10'}),null);
  assert.equal(selection.resolveSelection(bundle,{years:['3','5']}),null);
  assert.ok(selection.resolveSelection(bundle,{}));
  const duplicateExample=structuredClone(bundle);duplicateExample.examples.push(duplicateExample.examples[0]);
  assert.equal(selection.resolveSelection(duplicateExample,{}),null);
  const duplicateSnapshot=structuredClone(bundle);
  duplicateSnapshot.snapshots.push(duplicateSnapshot.snapshots.find(s=>s.example==='reference'&&s.years===3&&s.payload.selector.as_of==='2026-06-30'));
  assert.equal(selection.resolveSelection(duplicateSnapshot,{}),null);
});
test('actual server route rejects duplicate candidates from its saved bundle',async()=>{
  const bundle=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../apps/web/src/features/fundamentals/fixture.json'),'utf8'));
  function routeFor(data){
    const source=fs.readFileSync(path.resolve(__dirname,'../../apps/web/src/app/development/company/ratios/page.tsx'),'utf8');
    const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
    const module={exports:{}};
    new Function('module','exports','require',js)(module,module.exports,name=>{
      if(name==='node:fs/promises')return {readFile:async()=>JSON.stringify(data)};
      if(name==='node:path')return path;
      if(name==='next/navigation')return {notFound:()=>{throw new Error('not found')}};
      if(name==='react/jsx-runtime')return {jsx:(type,props)=>({type,props})};
      if(name==='@/features/fundamentals/selection')return selection;
      if(name==='@/features/fundamentals/FundamentalsWorkspace')return ()=>{};
      throw new Error('Unexpected import '+name);
    });
    return module.exports.default;
  }
  assert.ok((await routeFor(bundle)({searchParams:Promise.resolve({})})).props.saved);
  await assert.rejects(routeFor(bundle)({searchParams:Promise.resolve({yeas:'10'})}),/not found/);
  const duplicate=structuredClone(bundle);duplicate.snapshots.push(duplicate.snapshots.find(s=>s.example==='reference'&&s.years===3&&s.payload.selector.as_of==='2026-06-30'));
  await assert.rejects(routeFor(duplicate)({searchParams:Promise.resolve({})}),/not found/);
  const duplicateExample=structuredClone(bundle);duplicateExample.examples.push(duplicateExample.examples[0]);
  await assert.rejects(routeFor(duplicateExample)({searchParams:Promise.resolve({})}),/not found/);
});
