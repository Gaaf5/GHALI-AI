let labCatalog=[];
let labMixerOn=false;
const LAB_FALLBACK_CATALOG=[
  ["water","الماء","solvent"],["ethanol","الإيثانول","solvent"],["isopropanol","الأيزوبروبانول","solvent"],["methanol","الميثانول","solvent"],["acetone","الأسيتون","solvent"],["glycerol","الجليسرول","solvent"],
  ["urea","اليوريا","fertilizer"],["map","MAP","fertilizer"],["dap","DAP","fertilizer"],["mkp","MKP","fertilizer"],["sop","SOP","fertilizer"],["nop","نترات البوتاسيوم","fertilizer"],["ammonium_nitrate","نترات الأمونيوم","fertilizer"],["ammonium_sulfate","كبريتات الأمونيوم","fertilizer"],["urea_phosphate","فوسفات اليوريا","fertilizer"],["potassium_chloride","كلوريد البوتاسيوم","fertilizer"],["calcium_nitrate","نترات الكالسيوم","fertilizer"],
  ["magnesium_sulfate","كبريتات المغنيسيوم","salt"],["calcium_chloride","كلوريد الكالسيوم","salt"],["magnesium_nitrate","نترات المغنيسيوم","salt"],
  ["citric_acid","حمض الستريك","acid"],["sulfuric_acid","حمض الكبريتيك","acid"],["nitric_acid","حمض النيتريك","acid"],["phosphoric_acid","حمض الفوسفوريك","acid"]
].map(([id,name,kind])=>({id,name,kind}));
let labAnimation=null;
let labRunResult=null;
let labStartedAt=null;
const PARTICLE_COLORS={water:"#7ed9ff",urea:"#f3f3f3",map:"#e8d39a",dap:"#d8c08a",mkp:"#d7d0a5",sop:"#c9b985",nop:"#dce4ea"};
function labEsc(s){return esc(s)}
async function loadLabCatalog(){
  if(Array.isArray(labCatalog)&&labCatalog.length)return;
  try{
    const d=await api('/api/lab/materials');
    if(!Array.isArray(d)||!d.length)throw Error('Lab material catalog is empty');
    labCatalog=d;
  }catch(e){
    console.warn('Lab catalog API failed; using built-in catalog:',e);
    labCatalog=LAB_FALLBACK_CATALOG;
  }
}
function materialName(id){const m=labCatalog.find(x=>x.id===id);return m?m.name:id}
function materialKind(id){const m=labCatalog.find(x=>x.id===id);return m?m.kind:'solid'}
function labOptions(selected='water'){
  const groups={solvent:[],fertilizer:[],salt:[],acid:[]};
  labCatalog.forEach(m=>(groups[m.kind]||groups.fertilizer).push(m));
  const labels={solvent:'Solvents',fertilizer:'Fertilizers',salt:'Salts',acid:'Acids'};
  return Object.entries(groups).filter(([,a])=>a.length).map(([k,a])=>'<optgroup label="'+labels[k]+'">'+a.map(m=>'<option value="'+labEsc(m.id)+'"'+(m.id===selected?' selected':'')+'>'+labEsc(m.name)+' · '+labEsc(m.kind)+'</option>').join('')+'</optgroup>').join('');
}
function renumberRows(){
  const rows=[...document.querySelectorAll('.lab-add-row')];
  rows.forEach((r,i)=>{r.querySelector('.lab-order').textContent=i+1;});
  $('#labAdditionCount').textContent=rows.length+' material'+(rows.length===1?'':'s');
}
function addLabRow(material='water',mass=100,time=0){
  if(!labCatalog.length)labCatalog=LAB_FALLBACK_CATALOG;
  const box=$('#labAdditions'), row=document.createElement('div');
  row.className='lab-add-row';
  row.innerHTML='<span class="lab-order">1</span>'+
    '<select class="lab-material">'+labOptions(material)+'</select>'+
    '<input class="lab-mass" type="number" min="0" step="0.01" value="'+mass+'">'+
    '<input class="lab-add-time" type="number" min="0" step="1" value="'+time+'">'+
    '<div class="lab-row-actions"><button class="small lab-up" type="button">↑</button><button class="small lab-down" type="button">↓</button><button class="small lab-remove" type="button">×</button></div>';
  box.appendChild(row);
  row.querySelector('.lab-remove').onclick=()=>{row.remove();renumberRows()};
  row.querySelector('.lab-up').onclick=()=>{if(row.previousElementSibling)row.parentNode.insertBefore(row,row.previousElementSibling);renumberRows()};
  row.querySelector('.lab-down').onclick=()=>{if(row.nextElementSibling)row.parentNode.insertBefore(row.nextElementSibling,row);renumberRows()};
  renumberRows();
}
function labExperiment(){
  const volume=+$('#labVolume').value||0;
  const temp=+$('#labTemp').value;
  const rpm=+$('#labRpm').value||0;
  const duration=+$('#labTime').value||0;
  const playback=+$('#labPlayback').value||1;
  if(volume<0.1||volume>1000)throw Error('Working volume must be between 0.1 and 1000 L.');
  if(!Number.isFinite(temp)||temp<-50||temp>180)throw Error('Temperature must be between -50 and 180 °C.');
  if(rpm<0||rpm>1800)throw Error('Agitation must be between 0 and 1800 RPM.');
  if(duration<0||duration>86400)throw Error('Experiment time must be between 0 and 86400 s.');
  if(playback<0.25||playback>100)throw Error('Playback speed must be between 0.25× and 100×.');
  const additions=[...document.querySelectorAll('.lab-add-row')].map((r,i)=>({
    order:i+1,material:r.querySelector('.lab-material').value,
    mass_g:+r.querySelector('.lab-mass').value||0,time_s:+r.querySelector('.lab-add-time').value||0
  }));
  if(!additions.length)throw Error('Add at least one material before starting the experiment.');
  if(additions.some(a=>a.mass_g<=0))throw Error('Every material must have a mass greater than 0 g.');
  if(additions.some(a=>a.time_s<0||a.time_s>duration))throw Error('Each addition time must be within the experiment duration.');
  return {vessel:{working_volume_l:volume},temperature_c:temp,
    rpm:labMixerOn?rpm:0,duration_s:duration,additions};
}
function setLabState(state){$('#labState').textContent=state;$('#simStatus').textContent=state;}
function formatClock(sec){sec=Math.max(0,sec);return String(Math.floor(sec/60)).padStart(2,'0')+':'+(sec%60).toFixed(1).padStart(4,'0');}
function resetSimulator(){
  if(labAnimation)cancelAnimationFrame(labAnimation); labAnimation=null; labRunResult=null; labStartedAt=null;
  $('#simParticles').innerHTML='';$('#simPrecipitate').innerHTML='';
  $('#simLiquid').setAttribute('y','300');$('#simLiquid').setAttribute('height','260');
  $('#simSurface').setAttribute('d','M86 300 Q210 287 334 300');
  $('#simImpeller').classList.remove('spinning');$('#simSwirl').classList.remove('swirling');$('#labMixerToggle').textContent='Mixer OFF';$('#labMixerToggle').classList.remove('on');labMixerOn=false;
  $('#labClock').textContent='00:00.0';$('#simStartedAt').textContent='Not started';$('#simOverlay').innerHTML='<b>READY</b><span>Add materials and start the experiment</span>';
  $('#labEvents').innerHTML='<div class="empty">Start an experiment to see additions and dissolution events here.</div>';
  $('#labDissolution').innerHTML='<div class="empty">No materials yet.</div>';setLabState('READY');
}
function makeParticle(x,y,r=4,color='#ddd'){
  const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',x);c.setAttribute('cy',y);
  c.setAttribute('r',r);c.setAttribute('fill',color);c.setAttribute('opacity','.9');return c;
}
function spawnParticles(material,mass){
  const color=PARTICLE_COLORS[material]||'#ddd', count=Math.max(8,Math.min(70,Math.round(Math.sqrt(Math.max(mass,1))*2)));
  const frag=document.createDocumentFragment();
  for(let i=0;i<count;i++){const x=112+Math.random()*196,y=315+Math.random()*155;frag.appendChild(makeParticle(x,y,1.5+Math.random()*3,color));}
  $('#simParticles').appendChild(frag);
}
function renderPrecipitate(amount){
  $('#simPrecipitate').innerHTML='';
  if(amount<=0.001)return;
  const count=Math.max(8,Math.min(90,Math.round(amount)));
  const frag=document.createDocumentFragment();
  for(let i=0;i<count;i++)frag.appendChild(makeParticle(105+Math.random()*210,482+Math.random()*30,1.2+Math.random()*2,'#d4d0bd'));
  $('#simPrecipitate').appendChild(frag);
}
function renderEvents(result){
  const events=[...(result.events||[])].sort((a,b)=>a.time_s-b.time_s);
  $('#labEvents').innerHTML=events.length?events.map(e=>'<div class="lab-event"><b>'+formatClock(e.time_s)+'</b><span>'+labEsc(e.event==='add_solid'?'Added '+materialName(e.material):'Added '+materialName(e.material))+'</span><em>'+Number(e.mass_g||0).toFixed(2)+' g</em></div>').join(''):'<div class="empty">No events.</div>';
}
function renderDissolution(result){
  const rows=Object.entries(result.dissolution||{});
  if(!rows.length){$('#labDissolution').innerHTML='<div class="empty">No solid materials were added.</div>';return;}
  $('#labDissolution').innerHTML=rows.map(([id,x])=>{
    const pct=Math.max(0,Math.min(100,x.final_pct||0));
    const status=x.complete?'DISSOLVED':(x.precipitated?'PRECIPITATE / SOLID REMAINS':'SOLID REMAINS');
    return '<div class="diss-row"><div class="diss-top"><b>'+labEsc(materialName(id))+'</b><span>'+status+'</span></div>'+
      '<div class="diss-bar"><i style="width:'+pct.toFixed(1)+'%"></i></div>'+
      '<div class="diss-meta"><span>'+pct.toFixed(1)+'% dissolved</span><span>'+(x.time_to_95_s==null?'95% not reachable':Number(x.time_to_95_s).toFixed(1)+' s to 95%')+'</span></div></div>';
  }).join('');
}
function renderResult(d){
  $('#labConfidence').textContent=(d.confidence||'screening').toUpperCase();
  const u=d.mass_balance.undissolved_solids_g;
  const rows=Object.entries(d.dissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(materialName(k))+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const left=Object.entries(d.undissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(materialName(k))+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const risks=(d.chemistry?.compatibility_risks||[]).map(x=>'<div class="lab-warning">⚗ '+labEsc(x.message)+'</div>').join('');
  const warns=(d.warnings||[]).map(x=>'<div class="lab-warning">⚠ '+labEsc(x)+'</div>').join('');
  $('#labResult').innerHTML='<div class="lab-kpis"><div><span>Uniformity</span><b>'+d.mixing_uniformity_pct.toFixed(1)+'%</b></div>'+
    '<div><span>Undissolved</span><b>'+u.toFixed(2)+' g</b></div><div><span>Density</span><b>'+d.estimated_density_g_ml.toFixed(3)+' g/mL</b></div></div>'+
    '<h4>Dissolved</h4>'+rows+(left?'<h4>Undissolved / precipitate</h4>'+left:'')+
    (risks?'<h4>Compatibility / precipitation screen</h4>'+risks:'')+warns+
    '<div class="lab-model">'+labEsc(d.note)+'</div>';
  renderDissolution(d);renderEvents(d);
}
function animateExperiment(result){
  if(labAnimation)cancelAnimationFrame(labAnimation);
  const duration=Math.max(0,+$('#labTime').value||1), speed=Math.max(.25,+$('#labPlayback').value||1);
  const additions=(result.events||[]).filter(e=>e.event==='add_solid'||e.event==='add_solvent').sort((a,b)=>a.time_s-b.time_s);
  const dissolved=result.dissolution||{};
  const start=performance.now();labStartedAt=new Date();$('#simStartedAt').textContent='Started '+labStartedAt.toLocaleTimeString();let lastT=-1,added=new Set();
  $('#simParticles').innerHTML='';$('#simPrecipitate').innerHTML='';
  if(labMixerOn){$('#simImpeller').classList.add('spinning');$('#simSwirl').classList.add('swirling');}else{$('#simImpeller').classList.remove('spinning');$('#simSwirl').classList.remove('swirling');}setLabState('RUNNING');
  $('#simOverlay').innerHTML='<b>MIXING</b><span>Particles and dissolution are being simulated</span>';
  function frame(now){
    const t=Math.min(duration,(now-start)/1000*speed);
    const h=Math.min(260,Math.max(25,260*(0.18+0.82*Math.min(1,t/duration))));
    $('#simLiquid').setAttribute('y',String(560-h));$('#simLiquid').setAttribute('height',String(h));
    $('#simSurface').setAttribute('d','M86 '+(560-h)+' Q210 '+(547-h)+' 334 '+(560-h));
    $('#labClock').textContent=formatClock(t);$('#simRpm').textContent=Math.round(+$('#labRpm').value||0)+' RPM';$('#simTemp').textContent=(+$('#labTemp').value||20).toFixed(1)+' °C';
    additions.filter(e=>e.time_s<=t&&!added.has(e.material+'@'+e.time_s)).forEach(e=>{
      added.add(e.material+'@'+e.time_s);spawnParticles(e.material,e.mass_g);
      const name=materialName(e.material);$('#simOverlay').innerHTML='<b>ADD '+labEsc(name).toUpperCase()+'</b><span>'+Number(e.mass_g).toFixed(2)+' g enters the vessel</span>';
    });
    Object.entries(dissolved).forEach(([id,x])=>{
      const p=Math.max(0,Math.min(1,(t-(x.start_s||0))/Math.max(x.time_to_95_s||1,1)));
      [...$('#simParticles').children].forEach((node,i)=>{if(i%7===0&&p>.25)node.setAttribute('opacity',String(Math.max(.05,1-p)));});
    });
    const residue=Object.values(dissolved).reduce((s,x)=>s+(x.undissolved_g||0),0);renderPrecipitate(residue);
    if(t<duration){labAnimation=requestAnimationFrame(frame);}
    else{setLabState('COMPLETE');$('#simOverlay').innerHTML='<b>COMPLETE</b><span>Simulation finished — inspect dissolution and precipitation results below</span>';$('#simImpeller').classList.remove('spinning');}
  }
  labAnimation=requestAnimationFrame(frame);
}
async function runLab(){
  try{
    const exp=labExperiment();$('#labResult').innerHTML='<div class="empty">Calculating chemistry and mass balance…</div>';
    const d=await api('/api/lab/run',{method:'POST',body:JSON.stringify(exp)});labRunResult=d;renderResult(d);animateExperiment(d);
    await loadLabHistory();
  }catch(e){
    $('#labResult').innerHTML='<div class="bad"><b>Experiment not started</b><br>'+labEsc(e.message)+'</div>';
    setLabState('ERROR');
  }
}
function rangeInclusive(a,b,step){
  a=+a;b=+b;step=Math.abs(+step||1);if(step<=0)return[];const out=[];
  if(a<=b){for(let x=a;x<=b+1e-9;x+=step)out.push(+x.toFixed(8));}
  else{for(let x=a;x>=b-1e-9;x-=step)out.push(+x.toFixed(8));}return out;
}
async function runLabSweep(){
  try{const base=labExperiment(),rpm=rangeInclusive($('#swR0').value,$('#swR1').value,$('#swRs').value),temp=rangeInclusive($('#swT0').value,$('#swT1').value,$('#swTs').value);
    const count=rpm.length*temp.length;$('#labSweepCount').textContent=count+' runs';if(count>1000000)throw Error('Reduce the sweep; maximum is 1,000,000 virtual runs per request.');
    const d=await api('/api/lab/sweep',{method:'POST',body:JSON.stringify({base,variables:{rpm,temperature_c:temp},max_runs:1000000})});
    $('#labSweepResult').innerHTML='<div class="lab-sweep-summary"><b>'+d.runs.toLocaleString()+' runs completed</b><span>Best screen: '+d.best.undissolved_g.toFixed(2)+' g undissolved · '+d.best.uniformity_pct.toFixed(1)+'% uniformity</span><code>'+labEsc(JSON.stringify(d.best.variables))+'</code></div>';
  }catch(e){$('#labSweepResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
async function loadLabHistory(){
  try{const d=await api('/api/lab/experiments');$('#labHistory').innerHTML=d.map(x=>'<div class="lab-history-row"><span><b>'+labEsc(x.name)+'</b><small>'+labEsc(x.created_at)+'</small></span><em>'+labEsc(String(x.result?.confidence||'screening'))+'</em></div>').join('')||'<span class="muted">No experiments yet.</span>';
  }catch(e){$('#labHistory').innerHTML='<span class="bad">'+labEsc(e.message)+'</span>'}
}
async function initLab(){
  try{await loadLabCatalog();if(!document.querySelector('.lab-add-row')){addLabRow('water',1000,0);addLabRow('map',10,1);}
    await loadLabHistory();resetSimulator();
  }catch(e){$('#labResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
$('#labAddRow').onclick=()=>addLabRow('urea',100,0);
$('#labMixerToggle').onclick=()=>{labMixerOn=!labMixerOn;$('#labMixerToggle').textContent=labMixerOn?'Mixer ON':'Mixer OFF';$('#labMixerToggle').classList.toggle('on',labMixerOn);if(labMixerOn){$('#simImpeller').classList.add('spinning');$('#simSwirl').classList.add('swirling');}else{$('#simImpeller').classList.remove('spinning');$('#simSwirl').classList.remove('swirling');}};
$('#labClear').onclick=()=>{document.querySelector('#labAdditions').innerHTML='';renumberRows();resetSimulator();};
$('#labReset').onclick=resetSimulator;
$('#labRun').onclick=runLab;$('#labSweep').onclick=runLabSweep;
(async()=>{await initLab()})();
