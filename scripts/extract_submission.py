#!/usr/bin/env python3
"""Extract public event facts from a URL. Missing facts stay missing for review."""
import json, os, re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from dateutil.parser import parse
import collect


def proposal(body):
    match=re.search(r'```json\s*(\{.*?\})\s*```',body,re.S)
    if match:
        data=json.loads(match[1])
        if not isinstance(data,dict):raise ValueError('Expected a submission object')
    else:
        match=re.search(r'(?:https?|webcal)://[^\s<>]+',body)
        if not match:raise ValueError('Please include a public event, feed, or page URL.')
        data={'kind':'auto','url':match[0].rstrip(').,')}
    data['url']=str(data.get('url','')).replace('webcal:','https:',1)
    p=urlparse(data['url'])
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port not in (None,80,443):raise ValueError('Use a public HTTP(S) link.')
    return data


def from_event(e):
    d={k:e.get(k) for k in ['title','url','organiser','location','topics','format','country','language','languageRequirement','interpretation','access','price','audienceCountries','audienceRegions']}
    d.update(kind='event',description=e.get('description','')[:600],start=e['start'][:10],end=e['end'][:10] if e.get('end') else None)
    if e['allDay']:
        if d['end']:d['end']=(date.fromisoformat(d['end'])-timedelta(days=1)).isoformat()
    else:
        start=datetime.fromisoformat(e['start']);end=datetime.fromisoformat(e['end']) if e.get('end') else None
        # A numeric offset is safely represented in UTC unless an IANA zone is given.
        tz=e.get('timezone')
        try:ZoneInfo(tz)
        except (ValueError,TypeError,KeyError):tz='UTC' if start.tzinfo else None
        if tz and start.tzinfo:
            start=start.astimezone(ZoneInfo(tz));end=end.astimezone(ZoneInfo(tz)) if end else None
        d.update(start=start.date().isoformat(),end=end.date().isoformat() if end else None,startTime=start.strftime('%H:%M'),endTime=end.strftime('%H:%M') if end else None,timezone=tz)
    return d


def parse_manchester(soup,source,url):
    if urlparse(url).hostname!='events.manchester.ac.uk':return []
    fields={}
    for row in soup.select('table tr'):
        k,v=row.select_one('th'),row.select_one('td')
        if k and v:fields[k.get_text(' ',strip=True).rstrip(':')]=v.get_text(' ',strip=True)
    h=soup.select_one('h1');ds=fields.get('Dates','');times=re.findall(r'\d{1,2}:\d{2}',fields.get('Times',''))
    if not h or not re.fullmatch(r'\d{1,2} [A-Za-z]+ 20\d{2}',ds):return []
    start=parse(ds).date();end=start+timedelta(days=1)
    if times:
        start=datetime.combine(start,datetime.strptime(times[0],'%H:%M').time(),ZoneInfo('Europe/London'))
        end=datetime.combine(start.date(),datetime.strptime(times[-1],'%H:%M').time(),ZoneInfo('Europe/London')) if len(times)>1 else None
    body=soup.get_text(' ',strip=True)
    location='University of Manchester, Manchester, United Kingdom' if 'hosted at the University of Manchester' in body else ''
    e=collect.normalise(dict(title=h.get_text(' ',strip=True),start=start,end=end,organiser=fields.get('Organiser'),location=location,timezone='Europe/London',access=fields.get('Who is it for'),url=url),source,url)
    return [e] if e else []


def extract(data):
    url=data['url'];source={'id':'submission-preview','name':data.get('organiser') or urlparse(url).hostname,'topics':data.get('topics') or ['systems']}
    if data.get('timezone'):source['timezone']=data['timezone']
    text,final=collect.get(url)
    if text.lstrip().startswith('BEGIN:VCALENDAR'):
        return {'kind':'feed','url':url,'title':data.get('title') or source['name'],'organiser':source['name'],'topics':source['topics']},[]
    soup=BeautifulSoup(text,'html.parser');events=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            for raw in collect.walk_json(json.loads(script.string or script.get_text())):
                e=collect.json_event(raw,source,final)
                if e:events.append(e)
        except (ValueError,TypeError,AttributeError):continue
    events+=parse_manchester(soup,source,final)
    if urlparse(final).hostname in ('systemspractice.org','www.systemspractice.org'):events+=collect.parse_scio(soup,source,final)
    events=list({(e['url'],e['start']):e for e in events}.values())
    if len(events)==1:
        result=from_event(events[0]);result['url']=url
        # Optional human-supplied fields supplement published extraction, never erase it.
        for k,v in data.items():
            if v and k not in ('kind','url') and not (k in ('title','organiser') and re.match(r'https?://',str(v))):result[k]=v
        return result,[]
    title=data.get('title') or collect.clean(soup.select_one('h1').get_text() if soup.select_one('h1') else soup.title.get_text() if soup.title else '')[:180]
    result={**data,'title':title or source['name'],'organiser':data.get('organiser') or source['name']}
    if len(events)>1:
        return {**result,'kind':'page'},['This page contains several events. Review it as a source, or submit the individual event link.']
    if data.get('kind') in ('feed','page'):return result,[]
    # Keep arbitrary prose and ambiguous dates as evidence, not guessed calendar entries.
    return {**result,'kind':'event'},['No unambiguous event date was extracted. A maintainer needs to complete or classify this link before publication.']


def review_issue(payload):
    issue=payload['issue'];mark='<!-- systemsmap-extraction -->'
    try:
        data,notes=extract(proposal(issue.get('body','')))
        body=mark+'\nPublished details extracted for review. Nothing has been published to the map yet.\n\n```json\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n```'
        if notes:body+='\n\n'+'\n'.join(notes)
        body+='\n\nThe owner can copy corrected details into the issue and apply `approved`. A link-only approval is re-parsed before acceptance.'
    except Exception as exc:
        body=mark+'\nThis link needs a manual review: '+str(exc)[:350]+'. No event has been published.'
    api='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/issues/'+str(issue['number'])+'/comments'
    # The token is used only for GitHub, never for fetching the submitted URL.
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}
    r=collect.requests.get(api,headers=headers,params={'per_page':100},timeout=20);r.raise_for_status()
    previous=next((x for x in r.json() if x.get('user',{}).get('login')=='github-actions[bot]' and x.get('body','').startswith(mark)),None)
    if previous:r=collect.requests.patch('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/issues/comments/'+str(previous['id']),headers=headers,json={'body':body},timeout=20)
    else:r=collect.requests.post(api,headers=headers,json={'body':body},timeout=20)
    r.raise_for_status()

if __name__=='__main__':review_issue(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()))
