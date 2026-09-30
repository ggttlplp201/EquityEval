const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const ts=require('typescript');
const root=path.resolve(__dirname,'../..');
function load(file,resolve=()=>{throw new Error('Unexpected import')}){
 const js=ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
 const module={exports:{}};new Function('module','exports','require',js)(module,module.exports,resolve);return module.exports;
}
const selection=load('apps/web/src/features/company/selection.ts');
const bundle=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(root,'apps/web/src/features/company/fixture.json.gz'))));
test('Company exact selectors reject malformed and ambiguous candidates',()=>{
 const selected=selection.resolveSelection(bundle,{});
 assert.equal(selected.view.companyId,'computing-01');assert.equal(selected.view.asOf,'2026-06-30');
 for(const query of [{foo:'1'},{company:['computing-01','computing-01']},{asOf:['2026-06-30']},{company:''},{asOf:'2026-04-01'},{company:'CRCL'}]) assert.equal(selection.resolveSelection(bundle,query),null);
 const duplicate=structuredClone(bundle);duplicate.views.alias=duplicate.views['2026-06-30|computing-01'];assert.equal(selection.resolveSelection(duplicate,{}),null);
 const company=structuredClone(bundle);company.companies.push(company.companies[0]);assert.equal(selection.resolveSelection(company,{company:company.companies[0].id}),null);
 const dates=structuredClone(bundle);dates.context.asOfDates.push(dates.context.defaultAsOf);assert.equal(selection.resolveSelection(dates,{}),null);
 const wrongKey=structuredClone(bundle);wrongKey.views['2026-06-30|computing-01'].companyId='other';assert.equal(selection.resolveSelection(wrongKey,{}),null);
});
const overview=load('apps/web/src/features/company/overview.ts');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'apps/web/src/features/company/overview.json')));
test('linkage evidence retains exact selected metadata and supplied counts',()=>{
 const view=selection.resolveSelection(bundle,{}).view;
 const copy=structuredClone(manifest);copy.entries[view.id].counts.separate=17;
 const result=overview.overviewEvidence(copy,view);
 assert.equal(result.data.counts.separate,17);
 const text=JSON.stringify(result.detail);
 for(const expected of [view.id,view.snapshotId,'17','security_id: proof unavailable','issuer_id: mismatch','c'.repeat(64)])assert.ok(text.includes(expected),expected);
 assert.ok(!text.includes('100.1234567'),'no foreign financial amounts');
 assert.equal(result.data.cards[0].href,'/development/company?company=computing-01&asOf=2026-06-30');
 for(const card of result.data.cards.slice(1)){assert.equal(card.status,'separate');assert.ok(!card.href.includes('?'));}
 copy.entries[view.id].identity.issuer_id='other';assert.throws(()=>overview.overviewEvidence(copy,view),/mismatch/);
 for(const years of ['3','5','10']){
   const detail=overview.historyEvidence(view,years,bundle.details[view.detailId]);
   assert.equal(detail.sections[0].rows.find(r=>r.label==='Requested years').value,years);
   assert.deepEqual(JSON.parse(detail.sections[0].rows.find(r=>r.label==='missingDates').value),view.history[years].missingDates);
 }
});
test('research cards pass through statuses, counts, N/A and links without inference',()=>{
 const jsx=(type,props)=>({type,props});let opened;
 const Workspace=load('apps/web/src/features/company/ResearchWorkspace.tsx',name=>name==='react/jsx-runtime'?{jsx,jsxs:jsx}:name);
 const data=structuredClone(overview.overviewEvidence(manifest,selection.resolveSelection(bundle,{}).view).data);
 data.counts.separate=19;data.cards[1]={...data.cards[1],href:null,status:'unavailable',statusLabel:'N/A',name:null,asOf:null,navigationLabel:'N/A'};
 const tree=Workspace.default({data,onDetail:id=>opened=id});
 function nodes(n){return !n||typeof n!=='object'?[]:[n,...[n.props?.children].flat(Infinity).flatMap(nodes)];}
 const all=nodes(tree);const count=all.find(n=>n.props?.['data-linkage-count']==='separate');
 assert.deepEqual(count.props.children,['separate',': ',19]);count.props.onClick();assert.equal(opened,data.detailId);
 const card=all.find(n=>n.props?.['data-workspace']==='financials');assert.equal(card.props['data-linkage'],'unavailable');assert.ok(!nodes(card).some(n=>n.type==='next/link'));
 assert.ok(nodes(card).some(n=>n.props?.children==='N/A'));
});
test('Company actual server route checks file hashes and sends only selected history',async()=>{
 const createRoute=(queryBundle=bundle,queryManifest=manifest,stale=false)=>load('apps/web/src/app/development/company/page.tsx',name=>{
  if(name==='node:fs/promises')return {readFile:async file=>{
   if(file.endsWith('company/overview.json'))return JSON.stringify(queryManifest);
   if(file.endsWith('company/fixture.json.gz'))return zlib.gzipSync(JSON.stringify(queryBundle));
   const relative=file.slice(file.indexOf('src/features/')+13);
   return stale?Buffer.from('stale'):fs.readFileSync(path.join(root,'apps/web/src/features',relative));
  }};
  if(name==='node:crypto')return require(name);
  if(name==='node:path')return path;
  if(name==='node:zlib')return zlib;
  if(name==='node:util')return require(name);
  if(name==='next/navigation')return {notFound:()=>{throw new Error('not found')}};
  if(name==='react/jsx-runtime')return {jsx:(type,props)=>({type,props})};
  if(name==='@/features/company/selection')return selection;
  if(name==='@/features/company/overview')return overview;
  if(name==='@/features/company/CompanyWorkspace')return ()=>{};
  throw new Error(name);
 }).default;
 const checked=structuredClone(manifest);checked.files['company/fixture.json.gz']=require('node:crypto').createHash('sha256').update(zlib.gzipSync(JSON.stringify(bundle))).digest('hex');
 const page=await createRoute(bundle,checked)({searchParams:Promise.resolve({asOf:'2026-03-31'})});
 assert.equal(page.props.data.views.length,1);assert.equal(page.props.data.views[0].asOf,'2026-03-31');
 assert.ok(Object.keys(page.props.data.details).every(id=>!id.startsWith('company|2026-06-30')));
 for(const query of [{foo:'1'},{company:['computing-01']},{asOf:'2026-04-01'}])await assert.rejects(createRoute()({searchParams:Promise.resolve(query)}),/not found/);
 await assert.rejects(createRoute(bundle,checked,true)({searchParams:Promise.resolve({})}),/Stale/);
 const bad=structuredClone(checked);delete bad.files['valuation/fixture.json'];await assert.rejects(createRoute(bundle,bad)({searchParams:Promise.resolve({})}),/roster/);
});
test('Overview rounds exact decimal strings and preserves raw fixture precision',()=>{
 const p=load('apps/web/src/features/valuation/presentation.ts');
 const view=selection.resolveSelection(bundle,{}).view;
 for(const metric of view.metrics){const value=p.number(metric.value,metric.unit==='fraction');assert.ok(!/\.\d{5}/.test(value));}
 assert.equal(p.number(null),'N/A');assert.equal(p.number('0.123456789',true),'12.3457%');
 assert.equal(p.exact('34.472049689440993788819875776397515527950310559006'),'34.472049689440993788819875776397515527950310559006');
 const source=fs.readFileSync(path.join(root,'apps/web/src/features/company/CompanyWorkspace.tsx'),'utf8');
 assert.ok(!source.includes('.valueLabel}'));assert.ok(!source.includes('parseFloat('));assert.ok(source.includes('valueLabel(metric.value, metric.unit)'));
});
test('Overview formatting retains units and concise missing context',()=>{
 const p=load('apps/web/src/features/company/presentation.ts',name=>load('apps/web/src/features/valuation/presentation.ts'));
 assert.equal(p.valueLabel('1.234567','multiple'),'1.2346×');
 assert.equal(p.valueLabel('0.1234567','fraction'),'12.3457%');
 assert.equal(p.valueLabel('1234.567891','USD'),'$1,234.5679');
 assert.equal(p.valueLabel(null,'USD'),'N/A');
 const source=fs.readFileSync(path.join(root,'apps/web/src/features/company/CompanyWorkspace.tsx'),'utf8');
 assert.ok(source.includes('matching gross profit and consolidated net income were not supplied'));
 assert.ok(source.includes('Cash, debt, assets, liabilities and equity are not supplied'));
});
function renderCompany(companyId='computing-01',metric='operating_margin'){
 let opened;const jsx=(type,props)=>({type,props});
 const Component=load('apps/web/src/features/company/CompanyWorkspace.tsx',name=>{
  if(name==='react')return {useState:initial=>[initial==='operating_margin'?metric:initial,value=>opened=value],useTransition:()=>[false,()=>{}]};
  if(name==='next/navigation')return {useRouter:()=>({push:()=>{}})};
  if(name==='react/jsx-runtime')return {jsx,jsxs:jsx};
  if(name==='./presentation')return load('apps/web/src/features/company/presentation.ts',()=>load('apps/web/src/features/valuation/presentation.ts'));
  return name;
 }).default;
 const view=bundle.views['2026-06-30|'+companyId];
 const data={...bundle,company:bundle.companies.find(c=>c.id===companyId),views:Object.values(bundle.views).filter(v=>v.companyId===companyId),selectedAsOf:view.asOf,overview:overview.overviewEvidence(manifest,view).data};
 return {tree:Component({data}),opened:()=>opened};
}
function allNodes(n){return !n||typeof n!=='object'?[]:[n,...[n.props?.children].flat(Infinity).flatMap(allNodes)];}
function textOf(n){return typeof n==='string'?n:Array.isArray(n)?n.map(textOf).join(''):n&&typeof n==='object'?textOf(n.props?.children):'';}
test('missing explanations stay in their corresponding financial panels',()=>{
 const {tree}=renderCompany();const nodes=allNodes(tree);
 const contexts={'profitability-title':'matching gross profit and consolidated net income were not supplied','cash-title':'Separate CFO and cash PPE operands are not available','valuation-title':'Price per share, EPS, forward P/E and a valuation range are unavailable'};
 for(const [section,phrase] of Object.entries(contexts)){
  const content=textOf(nodes.find(n=>n.type==='section'&&n.props['aria-labelledby']===section));
  assert.ok(content.includes(phrase),section);
  for(const other of Object.values(contexts).filter(p=>p!==phrase))assert.ok(!content.includes(other));
 }
});
test('each unavailable historical date opens its own original snapshot evidence',()=>{
 const render=renderCompany('computing-12','pe');
 const view=bundle.views['2026-06-30|computing-12'];
 for(const point of view.history['3'].charts.pe.points){
  assert.ok(view.history['3'].charts.pe.unavailableDates.includes(point.date));
  const button=allNodes(render.tree).find(n=>n.type==='button'&&textOf(n)===point.date+' ↗ ');
  assert.ok(button);button.props.onClick();assert.equal(render.opened(),point.detailId);
 }
});
