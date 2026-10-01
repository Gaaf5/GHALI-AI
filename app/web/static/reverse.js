let reverseMaterials=[],reverseInitialized=false;
async function loadReverseMaterials(){
  reverseMaterials=await api('/api/materials');
}
function reverseMaterialOptions(selected){
  return reverseMaterials.filter(m=>m.active).map(m=>'<option value="'+esc(m.name)+'" '+(m.name===selected?'selected':'')+'>'+esc(m.name)+'</option>').join('');
}
function addReverseRow(name='',kg=''){
  const row=document.createElement('div'); row.className='reverse-row';
  row.innerHTML='<select class="reverse-material"><option value="">Select raw material</option>'+reverseMaterialOptions(name)+'</select><input class="reverse-kg" type="number" min="0" step="0.001" placeholder="kg" value="'+esc(kg)+'"><button class="small reverse-remove" type="button">×</button>';
  row.querySelector('.reverse-remove').onclick=()=>row.remove();
  $('#reverseRows').append(row);
}
function renderReverseResult(d){
  const b=d.nutrient_breakdown||{},f=b.nitrogen_forms_kg||{},fp=b.nitrogen_forms_pct_of_product||{};
  const rows=(d.materials||[]).map(m=>'<div class="resrow"><span>'+esc(m.name)+'</span><b>'+Number(m.kg).toFixed(3)+' kg</b></div>').join('');
  const traces=Object.entries(b.trace_elements_pct_of_product||{}).map(([k,v])=>'<div class="resrow"><span>'+esc(k)+'</span><b>'+Number(v*10000).toFixed(2)+' ppm</b></div>').join('');
  $('#reverseResult').innerHTML='<div class="status-banner good"><b>ANALYZED</b><span>'+Number(d.batch_kg).toFixed(3)+' kg</span></div><h4>Materials</h4>'+rows+'<h4>Final grade</h4>'+Object.entries(d.achieved||{}).map(([k,v])=>'<div class="resrow"><span>'+k+'</span><b>'+Number(v).toFixed(4)+'%</b></div>').join('')+'<h4>Secondary nutrients</h4><div class="resrow"><span>Sulfur</span><b>'+Number(b.sulfur_kg||0).toFixed(3)+' kg · '+Number(b.sulfur_pct_of_product||0).toFixed(4)+'%</b></div><div class="resrow"><span>Magnesium</span><b>'+Number(b.magnesium_kg||0).toFixed(3)+' kg · '+Number(b.magnesium_pct_of_product||0).toFixed(4)+'%</b></div><div class="resrow"><span>Chlorine</span><b>'+Number(b.chlorine_kg||0).toFixed(3)+' kg · '+Number(b.chlorine_pct_of_product||0).toFixed(4)+'%</b></div><h4>Nitrogen forms</h4><div class="resrow"><span>Nitrate-N</span><b>'+Number(f.nitrate_N||0).toFixed(3)+' kg · '+Number(fp.nitrate_N||0).toFixed(4)+'%</b></div><div class="resrow"><span>Ammoniacal-N</span><b>'+Number(f.ammoniacal_N||0).toFixed(3)+' kg · '+Number(fp.ammoniacal_N||0).toFixed(4)+'%</b></div><div class="resrow"><span>Ureic-N</span><b>'+Number(f.urea_N||0).toFixed(3)+' kg · '+Number(fp.urea_N||0).toFixed(4)+'%</b></div>'+(traces?'<h4>Trace elements</h4>'+traces:'');
}
async function initReverse(){
  if(reverseInitialized)return; reverseInitialized=true;
  try{await loadReverseMaterials(); addReverseRow();}catch(e){$('#reverseResult').innerHTML='<div class="bad">'+esc(e.message)+'</div>'}
  $('#reverseAdd').onclick=()=>addReverseRow();
  $('#reverseClear').onclick=()=>{$('#reverseRows').innerHTML='';$('#reverseResult').innerHTML='<div class="empty">Enter your existing raw-material quantities and analyze the blend.</div>';addReverseRow()};
  $('#reverseAnalyze').onclick=async()=>{try{const q={}; $$('#reverseRows .reverse-row').forEach(row=>{const n=row.querySelector('.reverse-material').value,k=Number(row.querySelector('.reverse-kg').value||0);if(n&&k>0)q[n]=(q[n]||0)+k}); const d=await api('/api/analyze-blend',{method:'POST',body:JSON.stringify({materials:q})}); renderReverseResult(d)}catch(e){$('#reverseResult').innerHTML='<div class="bad">'+esc(e.message)+'</div>'}};
}