#!/usr/bin/env python3
"""Accept an owner-reviewed issue; never fetch or execute an unreviewed submission."""
import json, os, re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from extract_submission import proposal, extract
ROOT=Path(__file__).resolve().parents[1]

def accept(payload):
    if payload.get('sender',{}).get('login')!=payload['repository']['owner']['login']:
        raise ValueError('Only the repository owner can approve publication through this workflow')
    if payload.get('label',{}).get('name')!='approved':return
    issue=payload['issue'];body=issue.get('body','')
    data=proposal(body)
    if data.get('kind')=='auto' or (data.get('kind')=='event' and not data.get('start')):
        data,notes=extract(data)
        if data.get('kind')=='event' and not data.get('start'):raise ValueError('; '.join(notes))
    kind=data.get('kind')
    if kind not in ('event','feed','page'):raise ValueError('Unknown submission type')
    for k,n in [('title',180),('url',1200),('organiser',120),('description',600),('location',300),('timezone',80),('language',120),('languageRequirement',300),('interpretation',300),('access',300)]:
        if data.get(k) is not None and (not isinstance(data[k],str) or len(data[k])>n):raise ValueError('Invalid '+k)
    p=urlparse(data.get('url','').replace('webcal:','https:',1))
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port not in (None,80,443):raise ValueError('Use a public HTTP(S) source')
    data['url']=p.geturl()
    for field in ['audienceCountries','audienceRegions']:
        values=data.get(field) or []
        if not isinstance(values,list) or len(values)>20 or any(not isinstance(v,str) or len(v)>120 for v in values):raise ValueError('Invalid '+field)
        data[field]=values
    if data.get('timezone'):ZoneInfo(data['timezone'])
    allowed={'systems','cybernetics','complexity','system-dynamics','systemic-design'}
    data['topics']=[x for x in data.get('topics',[]) if x in allowed] or ['systems']
    if kind in ('feed','page'):
        path=ROOT/'data/sources.json';sources=json.loads(path.read_text())
        entry={'id':'submitted-'+str(issue['number']),'name':data.get('title') or p.hostname,'url':data['url'],'adapter':'auto','topics':data['topics'],'region':'Community submitted','submission':issue['html_url']}
        if data.get('timezone'):entry['timezone']=data['timezone']
        if kind=='feed':entry.update(feeds=[data['url']],feedsExclusive=True,adapter='ics')
        sources=[s for s in sources if s['id']!=entry['id']]+[entry]
        path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    else:
        if not data.get('title') or not data.get('organiser'):raise ValueError('Event title and organiser must be extracted or completed before approval')
        if not data.get('start'):raise ValueError('An event needs a verified start date before approval')
        start=date.fromisoformat(data['start']);end=date.fromisoformat(data.get('end') or data['start'])
        if end<start:raise ValueError('End date precedes start')
        if data.get('startTime'):
            if not data.get('timezone'):raise ValueError('A timed event needs an IANA time zone before approval')
            start=datetime.fromisoformat(data['start']+'T'+data['startTime']).replace(tzinfo=ZoneInfo(data['timezone']))
            end=datetime.fromisoformat(end.isoformat()+'T'+data['endTime']).replace(tzinfo=ZoneInfo(data['timezone'])) if data.get('endTime') else None
        else:end+=timedelta(days=1)
        data.update(start=start.isoformat(),end=end.isoformat() if end else None,uid='submission-'+str(issue['number']),submission=issue['html_url'])
        path=ROOT/'data/approved-events.json';ev=json.loads(path.read_text()) if path.exists() else []
        ev=[e for e in ev if e['uid']!=data['uid']]+[data];path.write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n')
    print('Accepted reviewed submission',issue['number'])

if __name__=='__main__':accept(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()))
