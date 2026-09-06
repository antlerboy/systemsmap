#!/usr/bin/env python3
"""Import anonymous public submissions and prepare extraction for human review."""
import json
from pathlib import Path
import collect
from extract_submission import extract
ENDPOINT='https://events.transduction.systems/api/submissions'
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'dist/data/submission-review.json'
    old=json.loads(path.read_text()) if path.exists() else {'submissions':[]}
    entries={r['id']:r for r in old['submissions']}
    published={e['url'].rstrip('/') for e in json.loads((ROOT/'dist/data/events.json').read_text())['events']}
    try:
        offset=0;incoming=[]
        for _ in range(25):
            response=collect.requests.get(ENDPOINT,params={'offset':offset},timeout=20);response.raise_for_status();page=response.json()
            incoming.extend(page['submissions']);offset=page.get('nextOffset')
            if offset is None:break
    except Exception as e:
        print('Public submission inbox unavailable; existing review entries retained:',str(e)[:180]);return
    remaining=20
    for row in incoming:
        key=row['id'];known=entries.get(key)
        if row['url'].rstrip('/') in published:
            entries[key]={**row,'status':'published'};continue
        if known and known.get('status') in ('extracted','needs-review'):continue
        if remaining<=0:
            entries.setdefault(key,{**row,'status':'awaiting-extraction'});continue
        remaining-=1
        data={**row.get('proposal',{}),'url':row['url']}
        try:
            proposal,notes=extract(data)
            entries[key]={**row,'proposal':proposal,'notes':notes,'status':'needs-review' if notes else 'extracted','checkedAt':collect.STAMP}
        except Exception as e:
            entries[key]={**row,'status':'needs-review','notes':['Could not extract this link: '+str(e)[:220]],'checkedAt':collect.STAMP}
    path.write_text(json.dumps({'checkedAt':collect.STAMP,'submissions':list(entries.values())},ensure_ascii=False,indent=2)+'\n')
    print('Public submission review:',len(entries),'links; no automatic publication.')
if __name__=='__main__':main()
