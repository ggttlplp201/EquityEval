const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const root=path.resolve(__dirname,'../..');
function load(file,resolve=()=>{throw new Error('Unexpected import')}){
  const js=ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const module={exports:{}};new Function('module','exports','require',js)(module,module.exports,resolve);return module.exports;
}
const selection=load('apps/web/src/features/financials/selection.ts');
const bundle=JSON.parse(fs.readFileSync(path.join(root,'apps/web/src/features/financials/fixture.json')));
test('only exact saved basis and edition; no TTM or ambiguous selection',()=>{
  assert.equal(selection.resolveSelection(bundle,{}).edition,'annual_original');
  assert.equal(selection.resolveSelection(bundle,{basis:'quarter'}).edition,'quarter');
  for(const query of [{basis:'ttm'},{basis:'quarter',edition:'annual_original'},{edition:'absent'},{basis:['annual','quarter']},{unexpected:'1'},{edition:''}])assert.equal(selection.resolveSelection(bundle,query),null);
  const duplicate=structuredClone(bundle);duplicate.snapshots.push(duplicate.snapshots[0]);assert.equal(selection.resolveSelection(duplicate,{}),null);
  const duplicateChoice=structuredClone(bundle);duplicateChoice.choices.push(duplicateChoice.choices[0]);assert.equal(selection.resolveSelection(duplicateChoice,{}),null);
});
test('evidence uses exact decimal formatting and missing stays N/A',()=>{
  const p=load('apps/web/src/features/valuation/presentation.ts');
  assert.equal(p.number('100.1234567'),'100.1235');
  assert.equal(p.number(null),'N/A');
  assert.equal(p.number('0'),'0');
  assert.equal(p.exact(bundle.snapshots[0].statements[0].rows[0].value),'100.1234567');
});
test('server route sends selected snapshot only and fails closed',async()=>{
  const routeFor=data=>load('apps/web/src/app/development/company/financials/page.tsx',name=>{
    if(name==='node:fs/promises')return {readFile:async()=>JSON.stringify(data)};
    if(name==='node:path')return path;
    if(name==='next/navigation')return {notFound:()=>{throw new Error('not found')}};
    if(name==='react/jsx-runtime')return {jsx:(type,props)=>({type,props})};
    if(name==='@/features/financials/selection')return selection;
    if(name==='@/features/financials/FinancialsWorkspace')return ()=>{};
    throw new Error(name);
  }).default;
  const result=await routeFor(bundle)({searchParams:Promise.resolve({})});
  assert.equal(result.props.saved.edition,'annual_original');
  assert.ok(!JSON.stringify(result).includes('102.9876543'));
  assert.equal(result.props.snapshots,undefined);
  for(const query of [{foo:'1'},{basis:'ttm'},{edition:['annual_original','annual_revised']}])await assert.rejects(routeFor(bundle)({searchParams:Promise.resolve(query)}),/not found/);
  const duplicate=structuredClone(bundle);duplicate.snapshots.push(duplicate.snapshots[0]);await assert.rejects(routeFor(duplicate)({searchParams:Promise.resolve({})}),/not found/);
  const wrong=structuredClone(bundle);wrong.fictional=false;await assert.rejects(routeFor(wrong)({searchParams:Promise.resolve({})}),/Fictional/);
});
