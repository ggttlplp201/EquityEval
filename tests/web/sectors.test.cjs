const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const root=path.resolve(__dirname,'../..');
function load(file){
 const js=ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};new Function('module','exports','require',js)(module,module.exports,()=>({}));return module.exports;
}

test('sector history rescales to the selected series and preserves gaps',()=>{
 const {scaleHistory}=load('apps/web/src/features/sectors/history-scale.ts');
 const data={
  xAxis:{ticks:[],zero:60},
  yAxis:{ticks:[],zero:245},
  note:'fixture',
  series:[
   {sectorId:'computing',paths:[],points:[
    {asOf:'2025-09-30',x:60,y:40,valueLabel:'39.73×',status:'Eligible',detailId:'a'},
    {asOf:'2025-12-31',x:280,y:null,valueLabel:'—',status:'Missing inputs',detailId:'b'},
    {asOf:'2026-03-31',x:510,y:38,valueLabel:'40.30×',status:'Eligible',detailId:'c'},
    {asOf:'2026-06-30',x:730,y:36,valueLabel:'40.96×',status:'Eligible',detailId:'d'},
   ]},
   {sectorId:'energy',paths:[],points:[
    {asOf:'2025-09-30',x:60,y:180,valueLabel:'25.61×',status:'Eligible',detailId:'e'},
    {asOf:'2026-06-30',x:730,y:170,valueLabel:'27.51×',status:'Eligible',detailId:'f'},
   ]},
  ],
 };
 const scaled=scaleHistory(data,['computing']);
 assert.deepEqual(scaled.series.map(item=>item.sectorId),['computing']);
 const ys=scaled.series[0].points.filter(point=>point.y!==null).map(point=>point.y);
 assert.ok(Math.max(...ys)-Math.min(...ys)>180,'selected series should use most of the plot height');
 assert.equal(scaled.series[0].points[1].y,null);
 assert.equal(scaled.series[0].paths.length,2,'missing quarter remains a visible path break');
 assert.ok(scaled.yAxis.ticks.every(tick=>tick.label.endsWith('×')));
 assert.ok(!scaled.yAxis.ticks.some(tick=>tick.label==='0.00×'),'history axis should not force a zero baseline');
});
