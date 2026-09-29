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
function addLabRow(material='water',mass=100,time=0,particle=500){
  if(!labCatalog.length)labCatalog=LAB_FALLBACK_CATALOG;
  const box=$('#labAdditions'), row=document.createElement('div');
  row.className='lab-add-row';
  row.innerHTML='<span class="lab-order">1</span>'+
    '<select class="lab-material">'+labOptions(material)+'</select>'+
    '<input class="lab-mass" type="number" min="0.01" max="'+Math.max(1000,(+(document.querySelector('#labVolume')?.value)||1)*10000)+'" step="0.01" value="'+mass+'">'+
    '<input class="lab-particle" type="number" min="10" max="10000" step="10" value="'+particle+'" title="Particle size in micrometres">'+
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
    mass_g:+r.querySelector('.lab-mass').value||0,particle_size_um:+r.querySelector('.lab-particle').value||500,time_s:+r.querySelector('.lab-add-time').value||0
  }));
  if(!additions.length)throw Error('Add at least one material before starting the experiment.');
  if(additions.some(a=>!Number.isFinite(a.mass_g)||a.mass_g<=0))throw Error('Every material must have a finite mass greater than 0 g.');
  const maxAdditionMass=Math.max(1000,volume*10000);
  const totalCharge=additions.reduce((s,a)=>s+a.mass_g,0);
  if(additions.some(a=>a.mass_g>maxAdditionMass))throw Error('One material charge is too large for this vessel. Check for a duplicated or mis-scaled value.');
  if(totalCharge>maxAdditionMass*4)throw Error('Total charged mass is too large for this vessel. Check the timeline for a duplicated or mis-scaled input.');
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
  $('#labVessel').classList.remove('lab-vibrating');$('#labMixerToggle').textContent='Mixer OFF';$('#labMixerToggle').classList.remove('on');labMixerOn=false;
  $('#labClock').textContent='00:00.0';$('#simStartedAt').textContent='Not started';$('#simOverlay').innerHTML='<b>READY</b><span>Add materials and start the experiment</span>';
  $('#labEvents').innerHTML='<div class="empty">Start an experiment to see additions and dissolution events here.</div>';$('#labStateLedger').innerHTML='<div class="empty">Run an experiment to populate the event-time state ledger.</div>';
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
function renderUndissolved(amount){
  $('#simPrecipitate').innerHTML='';
  if(amount<=0.001)return;
  const count=Math.max(8,Math.min(90,Math.round(amount)));
  const frag=document.createDocumentFragment();
  for(let i=0;i<count;i++)frag.appendChild(makeParticle(105+Math.random()*210,482+Math.random()*30,1.2+Math.random()*2,'#d4d0bd'));
  $('#simPrecipitate').appendChild(frag);
}
function renderReactionTimeline(result){
  const steps=result.reaction_timeline||[];
  const box=$('#labReactionTimeline'), details=$('#labReactionDetails');
  if(!steps.length){box.innerHTML='<div class="empty">No chemical events yet.</div>';details.innerHTML='';return;}
  const additions=steps.filter(x=>x.event==='addition');
  const visualSteps=steps.filter(x=>x.event==='addition'||x.event==='equilibrium_shift'||x.event==='precipitation');
  box.innerHTML=visualSteps.map((x,i)=>{
    const formula=labEsc(x.display||x.material), label=labEsc(x.label||x.material);
    const next=visualSteps[i+1];
    const isShift=x.event==='equilibrium_shift';
    const isPrecip=x.event==='precipitation';
    const action=labEsc(x.action||(isPrecip?'↓ precipitate formed':('+ '+label)));
    const additionIndex=(isShift||isPrecip)?'-1':String(additions.indexOf(x));
    const eq=x.dissociation_equation?'<div class="rx-reaction"><b>'+((x.event==='equilibrium_shift')?'Equilibrium repartition:':'Dissociation:')+'</b> '+labEsc(x.dissociation_equation)+'</div>':(isPrecip&&x.equation?'<div class="rx-reaction"><b>Ksp precipitation:</b> '+labEsc(x.equation)+' · '+Number(x.precipitated_mass_g||0).toFixed(2)+' g predicted solid · Q/Ksp '+Number(x.Q_over_Ksp_before||0).toFixed(2)+(x.Q_over_Ksp_after!=null?' → '+Number(x.Q_over_Ksp_after).toFixed(2):'')+(x.estimated_crossing_time_s!=null?' · first crossing ≈ '+formatClock(x.estimated_crossing_time_s):'')+(x.kinetic_fraction!=null?' · kinetic fraction '+(Number(x.kinetic_fraction)*100).toFixed(1)+'%':'')+(x.supersaturation_order!=null?' · n='+Number(x.supersaturation_order).toFixed(1):'')+(x.temperature_factor!=null?' · T factor '+Number(x.temperature_factor).toFixed(2):'')+(x.induction_time_s!=null&&Number(x.induction_time_s)>0?' · induction '+Number(x.induction_time_s).toFixed(1)+' s':'')+(x.seed_factor!=null?' · seed '+Number(x.seed_factor).toFixed(2):'')+(x.surface_factor!=null?' · surface '+Number(x.surface_factor).toFixed(2):'')+'</div>':'');
    const st=x.material_state||{};
    const stateLine=(st.kinetic_dissolved_g!==undefined?'<div class="rx-state"><b>Actual kinetic state:</b> '+Number(st.kinetic_dissolved_g).toFixed(2)+' g dissolved · '+Number(st.kinetic_undissolved_g||0).toFixed(2)+' g solid</div>':'')+
      (st.event_equilibrium_target_g!==undefined?'<div class="rx-state"><b>After-event equilibrium target:</b> '+Number(st.event_equilibrium_target_g).toFixed(2)+' g dissolved</div>':'')+
      (st.pre_event_equilibrium_target_g!==undefined?'<div class="rx-state"><b>Before-event target:</b> '+Number(st.pre_event_equilibrium_target_g).toFixed(2)+' g</div>':'')+
      (st.equilibrium_undissolved_g!==undefined?'<div class="rx-state"><b>Equilibrium solid:</b> '+Number(st.equilibrium_undissolved_g).toFixed(2)+' g</div>':'')+
      (x.event==='addition' && x.dissociation?.length?'<div class="rx-state"><b>Dissociated species:</b> '+x.dissociation.map(labEsc).join(' + ')+'</div>':'')+
      (x.event==='addition' && x.acid_base_network?.length?'<div class="rx-state"><b>Candidate acid/base network:</b> '+x.acid_base_network.length+' equilibria · not event-time speciation</div>':'')+
      (x.event==='equilibrium_shift'?'<div class="rx-state"><b>Interpretation:</b> '+labEsc(x.description||'Shared aqueous-phase equilibrium changed; this is not a new chemical reaction.')+'</div>':'');
    return '<div class="reaction-step'+(isShift?' reaction-shift':'')+'" data-reaction-index="'+additionIndex+'"><div class="rx-time">t = '+formatClock(x.time_s)+'</div><div class="rx-main">'+action+'</div><div class="rx-sub"><b>'+formula+'</b> · '+labEsc(x.description||'Chemical addition')+'</div>'+stateLine+eq+'</div>'+(next?'<div class="reaction-arrow">→</div>':'');
  }).join('');
  const last=additions[additions.length-1]||steps[steps.length-1];
  const species=last?.species_after||[];
  const precip=steps.filter(x=>x.event==='precipitation');
  const networks=[...new Set(additions.flatMap(x=>x.acid_base_network||[]))];
  const finalSpecies=last?.final_calculated_species_mol_L||{};
  const finalRows=Object.entries(finalSpecies).sort((a,b)=>Number(b[1])-Number(a[1])).slice(0,12);
  details.innerHTML='<div class="rx-species">'+species.map(s=>'<span>'+labEsc(s)+'</span>').join('')+'</div>'+
    (last?.dissociation_equation?'<div class="rx-reaction"><b>Dissociation:</b> '+labEsc(last.dissociation_equation)+'</div>':'')+
    (networks.length?'<div class="rx-reaction"><b>Acid-base network (candidate equilibria):</b><br>'+networks.map(labEsc).join('<br>')+'</div>':'')+
    (finalRows.length?'<div class="rx-reaction"><b>Final calculated aqueous species:</b> '+finalRows.map(([k,v])=>labEsc(k)+' = '+Number(v).toExponential(3)+' M').join(' · ')+'<br><small>These values describe the final calculated state, not each event-time snapshot.</small></div>':'')+
    (precip.length?precip.map(x=>'<div class="rx-reaction"><b>Precipitation:</b> '+labEsc(x.display)+'</div>').join(''):'');
  $('#labReactionState').textContent=(result.quality?.confidence||'SCREENING').toUpperCase();
}
function renderChemicalStateMachine(result){
  const box=$('#labChemicalStateMachine');
  const states=result.chemical_state_machine||[];
  if(!states.length){box.innerHTML='<div class="empty">No scoped chemical states yet.</div>';return;}
  const stageLabel={input:'INPUT',dissolution:'DISSOLUTION',dissociation:'DISSOCIATION',acid_base_network:'ACID/BASE',speciation:'SPECIATION',equilibrium_repartition:'EQUILIBRIUM SHIFT',precipitation:'PRECIPITATION'};
  box.innerHTML=states.map(s=>{
    const detail=s.stage==='dissolution'?(s.dissolved_g!=null?'dissolved '+Number(s.dissolved_g).toFixed(2)+' g':s.target_dissolved_g!=null?'target '+Number(s.target_dissolved_g).toFixed(2)+' g':''):
      s.stage==='equilibrium_repartition'?'target '+Number(s.before_target_g).toFixed(2)+' → '+Number(s.after_target_g).toFixed(2)+' g':
      s.stage==='dissociation'?(s.equation||'principal ions: '+(s.species||[]).join(', ')):
      s.stage==='speciation'?'final-state calculation: '+Object.keys(s.species_mol_L||{}).length+' species':
      s.stage==='acid_base_network'?(s.equilibria||[]).length+' candidate equilibria':s.description||s.reaction||'';
    return '<div class="lab-event"><b>t='+formatClock(s.time_s)+'</b><span><strong>'+labEsc(stageLabel[s.stage]||s.stage)+'</strong> · '+labEsc(s.label||s.material)+'<br><small>'+labEsc(detail)+'</small></span><em>'+labEsc(s.scope||'')+'</em></div>';
  }).join('');
}
function renderStateLedger(result){
  const box=$('#labStateLedger');
  const timeline=result.state_timeline||{};
  const times=Object.keys(timeline).map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
  if(!times.length){box.innerHTML='<div class="empty">No deterministic event-time states yet.</div>';return;}
  box.innerHTML=times.map(t=>{
    const state=timeline[String(t)]||{};
    const rows=Object.entries(state).filter(([id,x])=>x&&typeof x==='object'&&('charged_g' in x || 'kinetic_dissolved_g' in x)).map(([id,x])=>{
      const actual=x.kinetic_dissolved_g==null?'-':Number(x.kinetic_dissolved_g).toFixed(2)+' g';
      const target=x.event_equilibrium_target_g==null?'-':Number(x.event_equilibrium_target_g).toFixed(2)+' g';
      const before=x.pre_event_equilibrium_target_g==null?'-':Number(x.pre_event_equilibrium_target_g).toFixed(2)+' g';
      const solid=x.equilibrium_undissolved_g==null?'-':Number(x.equilibrium_undissolved_g).toFixed(2)+' g';
      return '<div class="lab-event"><b>'+labEsc(materialName(id))+'</b><span>actual '+actual+' · target '+target+' · before '+before+'</span><em>solid '+solid+'</em></div>';
    }).join('');
    return '<div class="lab-event"><b>t = '+formatClock(t)+'</b><span>'+ (rows||'<span class="muted">No solid-state entries</span>') +'</span></div>';
  }).join('');
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
    const status=x.complete?'DISSOLVED':'UNDISSOLVED SOLID';
    const sol=x.solubility_g_per_100g_water;
    const src=x.solubility_source||'No source-backed curve';
    const eqMax=Number(x.equilibrium_max_pct??100);
    const t95Label=x.time_to_95_s!=null?Number(x.time_to_95_s).toFixed(1)+' s to 95%':(eqMax<95?'95% impossible at equilibrium':'95% not reached in run');
    const finalEq=x.final_mixed_equilibrium_capacity_g;
    const transientNote=(finalEq!=null && Number(x.final_dissolved_g||0)>Number(finalEq)+0.01)?'<div class="rx-state">Transient supersaturation: actual dissolved ('+Number(x.final_dissolved_g).toFixed(1)+' g) is above the final equilibrium target ('+Number(finalEq).toFixed(1)+' g); the model is still relaxing toward equilibrium.</div>':'';
    return '<div class="diss-row"><div class="diss-top"><b>'+labEsc(materialName(id))+'</b><span>'+status+'</span></div>'+
      '<div class="diss-bar"><i style="width:'+pct.toFixed(1)+'%"></i></div>'+
      '<div class="diss-meta"><span>'+pct.toFixed(1)+'% dissolved</span><span>'+t95Label+'</span></div>'+
      '<div class="diss-meta"><span>Equilibrium maximum: '+eqMax.toFixed(1)+'%</span><span>Loading: '+(Number(x.loading_ratio??0)*100).toFixed(1)+'% of mixed capacity</span></div>'+
      '<div class="diss-meta"><span>Pure-water capacity: '+(x.pure_water_capacity_g==null?'—':Number(x.pure_water_capacity_g).toFixed(1)+' g')+'</span><span>Capacity at addition: '+Number(x.equilibrium_capacity_at_addition_g??x.mixed_solution_effective_capacity_g??x.capacity_g??0).toFixed(1)+' g</span></div>'+
      '<div class="diss-meta"><span>Final mixed-equilibrium capacity: '+(x.final_mixed_equilibrium_capacity_g==null?'—':Number(x.final_mixed_equilibrium_capacity_g).toFixed(1)+' g')+'</span><span>Equilibrium state: t='+Number(x.equilibrium_state_time_s||0).toFixed(1)+' s</span></div>'+
      '<div class="diss-meta"><span>Peak dissolved: '+(x.peak_dissolved_g==null?'—':Number(x.peak_dissolved_g).toFixed(1)+' g')+'</span><span>Re-precipitated: '+(Number(x.reprecipitated_g||0)>0?Number(x.reprecipitated_g).toFixed(1)+' g':'—')+'</span></div>'+
      '<div class="diss-meta"><span>Shared capacity at addition: '+(x.shared_saturation_factor_at_addition==null?'—':(Number(x.shared_saturation_factor_at_addition)*100).toFixed(1)+'%')+'</span><span>Existing-solute load at addition: '+(x.other_solute_particle_ratio==null?'—':(Number(x.other_solute_particle_ratio)*100).toFixed(1)+'%')+'</span></div>'+
      '<div class="diss-meta"><span>Final shared saturation load: '+(x.final_shared_saturation_load==null?'—':(Number(x.final_shared_saturation_load)*100).toFixed(1)+'%')+'</span><span>Final shared capacity remaining: '+(x.final_shared_capacity_remaining==null?'—':(Number(x.final_shared_capacity_remaining)*100).toFixed(1)+'%')+'</span></div>'+
      '<div class="diss-meta"><span>Particle: '+Number(x.particle_size_um||500).toFixed(0)+' µm</span><span>Estimated t95: '+(x.kinetic_t95_estimate_s==null?'—':Number(x.kinetic_t95_estimate_s).toFixed(0)+' s')+'</span></div>'+
      transientNote+
      '<div class="diss-source"><span>'+labEsc(x.solubility_quality||'reference')+'</span> · '+labEsc(src)+(x.solubility_source_url?' · <a href="'+labEsc(x.solubility_source_url)+'" target="_blank" rel="noopener">Source</a>':'')+'</div></div>';
  }).join('');
}
function renderResult(d){
  $('#labConfidence').textContent=(d.confidence||'screening').toUpperCase();
  const u=d.mass_balance.undissolved_solids_g;
  const rows=Object.entries(d.dissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(materialName(k))+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const left=Object.entries(d.undissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(materialName(k))+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const risks=(d.chemistry?.compatibility_risks||[]).map(x=>'<div class="lab-warning">⚗ '+labEsc(x.message)+'</div>').join('');
  const multi=d.chemistry?.multicomponent||null;
  const multiFlags=(multi?.flags||[]).map(x=>'<div class="lab-warning">◌ '+labEsc(x)+'</div>').join('');
  const common=(multi?.common_ion_materials||[]).map(x=>labEsc(x.material)+': '+labEsc((x.common_ions||[]).join(', '))).join(' · ');
  const kspRows=(multi?.known_ksp_screen||[]).map(x=>'<div class="resrow"><span>'+labEsc(x.product)+' · '+labEsc(x.status)+'</span><b>Q/Ksp '+Number(x.Q_over_Ksp||0).toExponential(2)+'</b></div>').join('');
  const warns=(d.warnings||[]).map(x=>'<div class="lab-warning">⚠ '+labEsc(x)+'</div>').join('');
  const solventVol=d.conditions?.actual_solvent_volume_l;
  const blends=Object.entries(d.liquid_blending||{}).map(([k,x])=>'<div class="resrow"><span>'+labEsc(materialName(k))+' · '+Number(x.concentration_wt_pct||0).toFixed(0)+' wt%</span><b>t95 ≈ '+Number(x.blend_t95_estimate_s||0).toFixed(0)+' s</b></div>').join('');
  const ph=d.chemistry?.ph_estimate||null;
  const phRow=ph?.status==='screening'?'<div class="resrow"><span>Calculated pH (screening)</span><b>'+Number(ph.pH).toFixed(2)+'</b></div>':'';
  const speciesRows=ph?.status==='screening'?Object.entries(ph.species_mol_L||{}).filter(([,v])=>Number(v)>1e-8).sort((a,b)=>Number(b[1])-Number(a[1])).slice(0,16).map(([k,v])=>'<div class="resrow"><span>'+labEsc(k)+'</span><b>'+Number(v).toExponential(3)+' M</b></div>').join(''):'';
  const precipRows=(d.chemistry?.precipitation_equilibrium?.events||[]).map(x=>'<div class="resrow"><span>'+labEsc(x.product)+' precipitated</span><b>'+Number(x.precipitated_mol||0).toFixed(4)+' mol · Q/Ksp '+Number(x.Q_over_Ksp_before||0).toFixed(2)+'</b></div>').join('');
  const evidenceSeen=new Set();
  const evidenceRows=Object.entries(d.dissolution||[]).map(([id,x])=>{const e=x.evidence;if(!e||evidenceSeen.has(e.source_id))return '';evidenceSeen.add(e.source_id);return '<div class="resrow"><span>'+labEsc(e.source_name||e.source_id||'Source')+' · '+labEsc(e.confidence||'UNKNOWN')+'</span><b>'+(e.source_url?'<a href="'+labEsc(e.source_url)+'" target="_blank" rel="noopener">Reference</a>':'No URL')+'</b></div>';}).join('');
  const q=d.quality||{};
  const qModel=q.activity_model||{};
  const plans=(d.next_experiments||[]).map(x=>'<div class="resrow"><span><b>'+labEsc(x.id)+'</b> · '+labEsc(x.purpose)+'</span><b>'+labEsc(JSON.stringify(x.changes))+'</b></div>').join('');
  const qPanel='<h4>Model Quality & Uncertainty</h4>'+
    '<div class="resrow"><span>Confidence</span><b>'+labEsc(q.confidence||'UNKNOWN')+' · '+Number(q.score||0).toFixed(0)+'/100</b></div>'+
    '<div class="resrow"><span>Mass closure</span><b>'+Number(q.mass_closure_g||0).toFixed(3)+' g · error '+(Number(q.mass_closure_relative_error||0)*100).toFixed(4)+'%</b></div>'+
    '<div class="resrow"><span>Ionic strength</span><b>'+Number(q.ionic_strength_m||0).toFixed(3)+' M</b></div>'+
    '<div class="resrow"><span>Activity model</span><b>'+labEsc(qModel.activity_model||qModel.engine||'screening')+'</b></div>'+
    (plans?'<h4>Recommended Verification Experiments</h4>'+plans:'');
  $('#labResult').innerHTML='<div class="lab-kpis"><div><span>Uniformity</span><b>'+d.mixing_uniformity_pct.toFixed(1)+'%</b></div>'+
    '<div><span>Undissolved</span><b>'+u.toFixed(2)+' g</b></div><div><span>Solvent volume</span><b>'+(Number.isFinite(solventVol)?Number(solventVol).toFixed(3):'—')+' L</b></div><div><span>Density</span><b>'+d.estimated_density_g_ml.toFixed(3)+' g/mL</b></div></div>'+
    '<h4>Dissolved</h4>'+rows+(blends?'<h4>Liquid blending / homogenization</h4>'+blends:'')+(left?'<h4>Undissolved / precipitate</h4>'+left:'')+
    (multi?'<h4>Multicomponent solution screen</h4>'+phRow+'<div class="resrow"><span>Ionic strength</span><b>'+Number(multi.ionic_strength_mol_L||0).toFixed(4)+' mol/L</b></div><div class="resrow"><span>Equilibrium mode</span><b>Species / activity / Ksp screening</b></div>'+(common?'<div class="resrow"><span>Common ions detected</span><b>'+common+'</b></div>':'')+(kspRows?'<h4>Known Ksp screen</h4>'+kspRows:'')+(speciesRows?'<h4>Speciation</h4>'+speciesRows:'')+(precipRows?'<h4>Predicted precipitation</h4>'+precipRows:'')+multiFlags:'')+
    (risks?'<h4>Compatibility / precipitation screen</h4>'+risks:'')+
    (evidenceRows?'<h4>Evidence / References</h4>'+evidenceRows:'')+
    qPanel+warns+
    '<div class="lab-model">'+labEsc(d.note)+'</div>';
  renderDissolution(d);renderEvents(d);renderReactionTimeline(d);renderStateLedger(d);renderChemicalStateMachine(d);
}
function animateExperiment(result){
  if(labAnimation)cancelAnimationFrame(labAnimation);
  const duration=Math.max(0,+$('#labTime').value||1), speed=Math.max(.25,+$('#labPlayback').value||1);
  const additions=(result.events||[]).filter(e=>e.event==='add_solid'||e.event==='add_solvent'||e.event==='add_liquid').sort((a,b)=>a.time_s-b.time_s);
  const dissolved=result.dissolution||{};
  const start=performance.now();labStartedAt=new Date();$('#simStartedAt').textContent='Started '+labStartedAt.toLocaleTimeString();let lastT=-1,added=new Set();
  $('#simParticles').innerHTML='';$('#simPrecipitate').innerHTML='';
  if(labMixerOn){$('#labVessel').classList.add('lab-vibrating');}else{$('#labVessel').classList.remove('lab-vibrating');}setLabState('RUNNING');
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
    const activeIndex=additions.reduce((idx,e,i)=>e.time_s<=t?i:idx,-1);
    document.querySelectorAll('.reaction-step').forEach(el=>el.classList.toggle('active',Number(el.dataset.reactionIndex)===activeIndex));
    let liveResidue=0;
    Object.entries(dissolved).forEach(([id,x])=>{
      const elapsed=Math.max(0,t-(x.start_s||0));
      const tau=Math.max(1,Number(x.kinetic_tau_estimate_s||((x.kinetic_t95_estimate_s||x.time_to_95_s||1)/Math.log(20))));
      const equilibriumFraction=Math.max(0,Math.min(1,Number(x.capacity_g||0)/Math.max(Number(x.mass_g||1),1e-9)));
      const dissolvedFraction=Math.max(0,Math.min(equilibriumFraction,equilibriumFraction*(1-Math.exp(-elapsed/tau))));
      liveResidue+=Math.max(0,Number(x.mass_g||0)*(1-dissolvedFraction));
      const opacity=Math.max(.08,1-dissolvedFraction);
      [...$('#simParticles').children].forEach((node,i)=>{if(i%7===0)node.setAttribute('opacity',String(opacity));});
    });
    renderUndissolved(liveResidue);
    if(t<duration){labAnimation=requestAnimationFrame(frame);}
    else{setLabState('COMPLETE');$('#simOverlay').innerHTML='<b>COMPLETE</b><span>Simulation finished — inspect dissolution and undissolved-solid results below</span>';$('#labVessel').classList.remove('lab-vibrating');}
  }
  labAnimation=requestAnimationFrame(frame);
}
async function runLab(){
  try{
    const exp=labExperiment();$('#labResult').innerHTML='<div class="empty">Calculating chemistry and mass balance…</div>';
    $('#labAIReview').disabled=true;$('#labAIStatus').textContent='Run an experiment first.';$('#labAIReviewPanel').classList.add('hidden');$('#labAIReviewPanel').innerHTML='';
    const d=await api('/api/lab/run',{method:'POST',body:JSON.stringify(exp)});labRunResult=d;renderResult(d);animateExperiment(d);
    $('#labAIReview').disabled=false;$('#labAIStatus').textContent='Optional: ask the AI to audit the chemistry logic.';
    await loadLabHistory();
  }catch(e){
    $('#labResult').innerHTML='<div class="bad"><b>Experiment not started</b><br>'+labEsc(e.message)+'</div>';
    setLabState('ERROR');
  }
}
async function runLabAIReview(){
  if(!labRunResult)return;
  const button=$('#labAIReview');button.disabled=true;$('#labAIStatus').textContent='AI is reviewing the constrained simulation…';
  try{
    const d=await api('/api/lab/ai-review',{method:'POST',body:JSON.stringify({result:labRunResult})});
    $('#labAIReviewPanel').classList.remove('hidden');
    $('#labAIReviewPanel').innerHTML='<h4>✦ AI Chemistry Review</h4><div class="lab-ai-text">'+labEsc(d.review||'No review returned.').replace(/\n/g,'<br>')+'</div>';
    $('#labAIStatus').textContent='Review complete. AI cannot override deterministic chemistry.';
  }catch(e){
    $('#labAIStatus').textContent='AI review unavailable; deterministic simulation remains valid.';
  }finally{button.disabled=false;}
}
async function loadLabHistory(){
  try{const d=await api('/api/lab/experiments');$('#labHistory').innerHTML=d.map(x=>'<div class="lab-history-row"><span><b>'+labEsc(x.name)+'</b><small>'+labEsc(x.created_at)+'</small></span><em>'+labEsc(String(x.result?.confidence||'screening'))+'</em></div>').join('')||'<span class="muted">No experiments yet.</span>';
  }catch(e){$('#labHistory').innerHTML='<span class="bad">'+labEsc(e.message)+'</span>'}
}
async function loadLabEngine(){
  try{const r=await fetch('/api/lab/engine');const d=await r.json();const el=$('#labEngineStatus');if(el&&d.active)el.textContent=(d.active.engine||'unknown')+' · '+(d.phreeqc?.available?'PHREEQC ready':'screening fallback');}catch(e){}
}

async function initLab(){
  loadLabEngine();
  try{await loadLabCatalog();if(!document.querySelector('.lab-add-row')){addLabRow('water',1000,0);addLabRow('map',10,1);}
    await loadLabHistory();resetSimulator();
  }catch(e){$('#labResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
$('#labAddRow').onclick=()=>addLabRow('urea',100,0);
$('#labMixerToggle').onclick=()=>{labMixerOn=!labMixerOn;$('#labMixerToggle').textContent=labMixerOn?'Mixer ON':'Mixer OFF';$('#labMixerToggle').classList.toggle('on',labMixerOn);$('#labVessel').classList.toggle('lab-vibrating',labMixerOn);};
$('#labClear').onclick=()=>{document.querySelector('#labAdditions').innerHTML='';renumberRows();resetSimulator();};
$('#labReset').onclick=resetSimulator;
$('#labRun').onclick=runLab;
$('#labAIReview').onclick=runLabAIReview;
(async()=>{await initLab()})();
