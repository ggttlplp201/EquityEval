const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const root=path.resolve(__dirname,'../..');
const jsx=(type,props)=>({type,props:props??{}});

function load(file,resolver=()=>({})){
 const js=ts.transpileModule(fs.readFileSync(path.join(root,file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const module={exports:{}};
 new Function('module','exports','require',js)(module,module.exports,resolver);
 return module.exports;
}
function nodes(value){
 if(value==null||typeof value!=='object')return [];
 if(Array.isArray(value))return value.flatMap(nodes);
 return [value,...nodes(value.props?.children)];
}
function textContent(value){
 if(value==null||typeof value==='boolean')return '';
 if(typeof value==='string'||typeof value==='number')return String(value);
 if(Array.isArray(value))return value.map(textContent).join('');
 return textContent(value.props?.children);
}

const data={
 xAxis:{ticks:[],zero:60},
 note:'Quarter-end snapshots · gaps stay gaps.',
 series:[
  {sectorId:'computing',segments:[[0],[2,3]],points:[
   {asOf:'2025-09-30',x:60,valueLabel:'39.73×',status:'Eligible',detailId:'a'},
   {asOf:'2025-12-31',x:280,valueLabel:'—',status:'Missing inputs',detailId:'b'},
   {asOf:'2026-03-31',x:510,valueLabel:'40.30×',status:'Eligible',detailId:'c'},
   {asOf:'2026-06-30',x:730,valueLabel:'40.96×',status:'Eligible',detailId:'d'},
  ]},
  {sectorId:'energy',segments:[[0,1]],points:[
   {asOf:'2025-09-30',x:60,valueLabel:'25.61×',status:'Eligible',detailId:'e'},
   {asOf:'2026-06-30',x:730,valueLabel:'27.51×',status:'Eligible',detailId:'f'},
  ]},
 ],
 scales:{
  computing:{yAxis:{ticks:[{position:245,label:'39.63×'},{position:25,label:'41.06×'}],zero:999},yBySector:{computing:[230,null,142,40]}},
  'computing|energy':{yAxis:{ticks:[{position:245,label:'24.38×'},{position:25,label:'42.19×'}],zero:999},yBySector:{computing:[55,null,48,40],energy:[230,207]}},
 },
};

test('history component uses exporter-supplied focused and shared geometry',()=>{
 const charts=load('apps/web/src/features/sectors/charts.tsx',(name)=>{
  if(name==='react')return {useId:()=> 'history'};
  if(name==='react/jsx-runtime')return {jsx,jsxs:jsx,Fragment:'fragment'};
  throw new Error(`unexpected import ${name}`);
 });
 const props={data,slots:{computing:0,energy:1},sectors:[{id:'computing',label:'Computing'},{id:'energy',label:'Energy'}],onDetail:()=>{},describeDetail:()=>''};
 const focused=charts.HistoryChart({...props,selected:['computing']});
 const shared=charts.HistoryChart({...props,selected:['energy','computing']});
 const focusedAxis=nodes(focused).find(node=>node.type===charts.PlotAxes).props.yAxis;
 const sharedAxis=nodes(shared).find(node=>node.type===charts.PlotAxes).props.yAxis;

 assert.match(textContent(focused),/may not start at zero/);
 assert.equal(focusedAxis.ticks[0].label,'39.63×');
 assert.equal(sharedAxis.ticks[0].label,'24.38×');
 assert.equal(nodes(focused).filter(node=>node.type==='polyline').length,2,'missing quarter remains two segments');
 assert.equal(nodes(shared).filter(node=>node.type==='polyline').length,3,'two selected sectors use one shared scale');
 assert.notDeepEqual(
  nodes(focused).filter(node=>node.type==='polyline').map(node=>node.props.points),
  nodes(shared).filter(node=>node.type==='polyline').map(node=>node.props.points),
  'selection changes to the matching precomputed geometry',
 );
});

test('history chart source does not parse labels or calculate financial geometry',()=>{
 const source=fs.readFileSync(path.join(root,'apps/web/src/features/sectors/charts.tsx'),'utf8');
 assert.ok(!source.includes('parseFloat('));
 assert.ok(!source.includes('Number('));
 assert.ok(!source.includes('valueLabel.replace'));
 assert.ok(!fs.existsSync(path.join(root,'apps/web/src/features/sectors/history-scale.ts')));
});
