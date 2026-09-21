from __future__ import annotations
import json
from pathlib import Path
from itertools import product
from app.tools.lab import MATERIALS, simulate

OUT=Path('data/lab_scenarios/scenarios_10000.jsonl')
TARGET=10000
materials=list(MATERIALS)
temps=[5,15,25,35,45,55,65,75,85,95]
rpms=[100,200,300,450,600,750,900,1100,1400,1800]
times=[5,10,20,30,60,120,300,600,1200,2400]
volumes=[1,2,5,10,20,50,100,250,500,1000]
masses=[1,5,10,25,50,100,250,500,1000,2500]


def case(i):
    m=materials[i%len(materials)]
    j=i//len(materials)
    # Deterministic factorial-style coverage across operating variables.
    t=temps[j%10]; rpm=rpms[(j//10)%10]; dur=times[(j//100)%10]
    vol=volumes[(j//1000)%10]; mass=masses[(j//17)%10]
    if i>=len(materials)*10:
        m2=materials[(i*7+3)%len(materials)]
        if m2==m: m2=materials[(materials.index(m)+1)%len(materials)]
        return {'name':f'AUTO-{i+1:05d}','working_volume_l':vol,'temperature_c':t,'rpm':rpm,'duration_s':dur,'additions':[{'material':m,'mass_g':mass,'addition_time_s':0},{'material':m2,'mass_g':masses[(i//31)%10],'addition_time_s':dur//2}]}
    return {'name':f'AUTO-{i+1:05d}','working_volume_l':vol,'temperature_c':t,'rpm':rpm,'duration_s':dur,'additions':[{'material':m,'mass_g':mass,'addition_time_s':0}]}


def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    counts={m:0 for m in materials}; statuses={}; risks={}; total=0
    with OUT.open('w',encoding='utf-8') as f:
        for i in range(TARGET):
            x=case(i); r=simulate(x)
            f.write(json.dumps({'id':i+1,'input':x,'result':r},ensure_ascii=False,separators=(',',':'))+'\n')
            total+=1; counts[x['additions'][0]['material']]+=1
            s=str(r.get('status','UNKNOWN')); statuses[s]=statuses.get(s,0)+1
            for w in r.get('warnings',[]): risks[w]=risks.get(w,0)+1
    summary={'total':total,'materials':len(materials),'per_material_min':min(counts.values()),'per_material_max':max(counts.values()),'status_counts':statuses,'top_warnings':sorted(risks.items(),key=lambda x:-x[1])[:20],'output':str(OUT),'note':'Synthetic screening simulations, not validated experimental measurements.'}
    Path('data/lab_scenarios/scenarios_10000_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__': main()
