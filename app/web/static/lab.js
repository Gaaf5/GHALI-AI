let labCatalog=[];
function labEsc(s){return esc(s)}
async function loadLabCatalog(){
  if(labCatalog.length)return;
  labCatalog=await api('/api/lab/materials');
}
function labOptions(){
  return labCatalog.map(m=>'<option value="'+labEsc(m.id)+'">'+labEsc(m.name)+' · '+labEsc(m.kind)+'</option>').join('');
}
function addLabRow(material='sop',mass=100,time=0){
  const box=$('#labAdditions');
  const row=document.createElement('div'); row.className='lab-add-row';
  row.innerHTML='<select class="lab-material">'+labOptions()+'</select>'+
    '<input class="lab-mass" type="number" min="0" step="0.01" value="'+mass+'" placeholder="mass g">'+
    '<input class="lab-add-time" type="number" min="0" step="1" value="'+time+'" placeholder="add time s">'+
    '<button class="small lab-remove" type="button">×</button>';
  box.appendChild(row); row.querySelector('.lab-material').value=material;
  row.querySelector('.lab-remove').onclick=()=>row.remove();
}
function labExperiment(){
  const scale=Math.max(1,+$('#labTimeScale').value||1);
  const duration=Math.max(0,+$('#labTime').value||0)*scale;
  const additions=[...document.querySelectorAll('.lab-add-row')].map(r=>({
    material:r.querySelector('.lab-material').value,
    mass_g:+r.querySelector('.lab-mass').value||0,
    time_s:+r.querySelector('.lab-add-time').value||0
  }));
  return {vessel:{working_volume_l:+$('#labVolume').value||1},
    temperature_c:+$('#labTemp').value||20,rpm:+$('#labRpm').value||0,
    duration_s:duration,additions};
}
function renderLabResult(d){
  $('#labConfidence').textContent=(d.confidence||'screening').toUpperCase();
  const u=d.mass_balance.undissolved_solids_g;
  const rows=Object.entries(d.dissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(k)+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const left=Object.entries(d.undissolved_g||{}).map(([k,v])=>'<div class="resrow"><span>'+labEsc(k)+'</span><b>'+v.toFixed(3)+' g</b></div>').join('');
  const warns=(d.warnings||[]).map(x=>'<div class="lab-warning">⚠ '+labEsc(x)+'</div>').join('');
  $('#labResult').innerHTML='<div class="lab-kpis"><div><span>Uniformity</span><b>'+d.mixing_uniformity_pct.toFixed(1)+'%</b></div>'+
    '<div><span>Undissolved</span><b>'+u.toFixed(2)+' g</b></div><div><span>Density</span><b>'+d.estimated_density_g_ml.toFixed(3)+' g/mL</b></div></div>'+
    '<h4>Dissolved</h4>'+rows+(left?'<h4>Undissolved</h4>'+left:'')+
    ((d.chemistry?.compatibility_risks||[]).length?'<h4>Compatibility / precipitation screen</h4>'+d.chemistry.compatibility_risks.map(x=>'<div class="lab-warning">⚗ '+labEsc(x.message)+'</div>').join(''):'')+warns+
    '<div class="lab-model">'+labEsc(d.note)+'</div>';
}
async function runLab(){
  try{$('#labResult').innerHTML='<div class="empty">Running digital experiment…</div>';
    const d=await api('/api/lab/run',{method:'POST',body:JSON.stringify(labExperiment())}); renderLabResult(d); await loadLabHistory();
  }catch(e){$('#labResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
function rangeInclusive(a,b,step){
  a=+a;b=+b;step=Math.abs(+step||1);if(step<=0)return[];
  const out=[];if(a<=b){for(let x=a;x<=b+1e-9;x+=step)out.push(+x.toFixed(8));}
  else{for(let x=a;x>=b-1e-9;x-=step)out.push(+x.toFixed(8));}return out;
}
async function runLabSweep(){
  try{
    const base=labExperiment();
    const rpm=rangeInclusive($('#swR0').value,$('#swR1').value,$('#swRs').value);
    const temp=rangeInclusive($('#swT0').value,$('#swT1').value,$('#swTs').value);
    const count=rpm.length*temp.length; $('#labSweepCount').textContent=count+' runs';
    if(count>1000000)throw Error('Reduce the sweep; maximum is 1,000,000 virtual runs per request.');
    const d=await api('/api/lab/sweep',{method:'POST',body:JSON.stringify({base,variables:{rpm,temperature_c:temp},max_runs:1000000})});
    $('#labSweepResult').innerHTML='<div class="lab-sweep-summary"><b>'+d.runs.toLocaleString()+' runs completed</b>'+
      '<span>Best screen: '+d.best.undissolved_g.toFixed(2)+' g undissolved · '+d.best.uniformity_pct.toFixed(1)+'% uniformity</span>'+
      '<code>'+labEsc(JSON.stringify(d.best.variables))+'</code></div>';
  }catch(e){$('#labSweepResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
async function loadLabHistory(){
  try{const d=await api('/api/lab/experiments');
    $('#labHistory').innerHTML=d.map(x=>'<div class="lab-history-row"><span><b>'+labEsc(x.name)+'</b><small>'+labEsc(x.created_at)+'</small></span><em>'+labEsc(String(x.result?.confidence||'screening'))+'</em></div>').join('')||'<span class="muted">No experiments yet.</span>';
  }catch(e){$('#labHistory').innerHTML='<span class="bad">'+labEsc(e.message)+'</span>'}
}
async function initLab(){
  try{await loadLabCatalog();$('#labAdditions').innerHTML='';addLabRow('sop',100,0);addLabRow('water',1000,0); await loadLabHistory();}
  catch(e){$('#labResult').innerHTML='<div class="bad">'+labEsc(e.message)+'</div>'}
}
$('#labAddRow').onclick=()=>addLabRow('urea',100,0);
$('#labClear').onclick=()=>$('#labAdditions').innerHTML='';
$('#labRun').onclick=runLab; $('#labSweep').onclick=runLabSweep;
(async()=>{await initLab()})();

