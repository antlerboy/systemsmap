#!/usr/bin/env python3
"""Collect public event facts; retain provenance, uncertainty, and failed-source data."""
from __future__ import annotations
import concurrent.futures, hashlib, ipaddress, json, os, re, socket, sys, threading, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, quote, unquote
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo
import requests
import html
from bs4 import BeautifulSoup
from dateutil.parser import parse, isoparse
from icalendar import Calendar, Event
import recurring_ical_events

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)
WINDOW_START = NOW - timedelta(days=90)
WINDOW_END = NOW + timedelta(days=550)
STAMP = NOW.isoformat(timespec='seconds')
UA = 'SystemsEventsMap/1.0 (+https://github.com/antlerboy/systemsmap)'
TOPICS = {'systems':'Systems thinking','cybernetics':'Cybernetics','complexity':'Complexity','system-dynamics':'System dynamics','systemic-design':'Systemic design'}
CITIES = {
 'cranfield':(52.073,-0.628,'United Kingdom'), 'manchester':(53.480,-2.242,'United Kingdom'),
 'loughborough':(52.773,-1.207,'United Kingdom'), 'london':(51.507,-0.128,'United Kingdom'),
 'hull':(53.767,-0.328,'United Kingdom'), 'bristol':(51.455,-2.588,'United Kingdom'),
 'exeter':(50.719,-3.534,'United Kingdom'), 'woerden':(52.086,4.883,'Netherlands'),
 'amsterdam':(52.367,4.904,'Netherlands'), 'utrecht':(52.090,5.122,'Netherlands'),
 'brussels':(50.847,4.352,'Belgium'), 'antwerp':(51.219,4.402,'Belgium'),
 'vienna':(48.208,16.374,'Austria'), 'wien':(48.208,16.374,'Austria'),
 'turin':(45.070,7.686,'Italy'), 'torino':(45.070,7.686,'Italy'), 'ostana':(44.692,7.190,'Italy'),
 'pyla':(35.010,33.691,'Cyprus'), 'paphos':(34.775,32.424,'Cyprus'),
 'maribor':(46.554,15.646,'Slovenia'), 'ljubljana':(46.056,14.505,'Slovenia'),
 'são paulo':(-23.551,-46.633,'Brazil'), 'sao paulo':(-23.551,-46.633,'Brazil'),
 'rio de janeiro':(-22.906,-43.173,'Brazil'), 'buenos aires':(-34.604,-58.382,'Argentina'),
 'santiago':(-33.449,-70.669,'Chile'), 'bogotá':(4.711,-74.072,'Colombia'),
 'mexico city':(19.433,-99.133,'Mexico'), 'ciudad de méxico':(19.433,-99.133,'Mexico'),
 'santa fe':(35.687,-105.938,'United States'), 'boston':(42.360,-71.059,'United States'),
 'new york':(40.713,-74.006,'United States'), 'washington':(38.907,-77.037,'United States'),
 'chicago':(41.878,-87.630,'United States'), 'seattle':(47.606,-122.332,'United States'),
 'san francisco':(37.775,-122.419,'United States'), 'los angeles':(34.052,-118.244,'United States'),
 'toronto':(43.653,-79.383,'Canada'), 'montreal':(45.501,-73.567,'Canada'),
 'vancouver':(49.283,-123.121,'Canada'), 'paris':(48.857,2.352,'France'),
 'lyon':(45.764,4.836,'France'), 'berlin':(52.520,13.405,'Germany'),
 'hamburg':(53.551,9.994,'Germany'), 'bremen':(53.079,8.802,'Germany'),
 'barcelona':(41.387,2.169,'Spain'), 'lisbon':(38.722,-9.139,'Portugal'),
 'porto':(41.158,-8.629,'Portugal'), 'warsaw':(52.229,21.012,'Poland'),
 'oslo':(59.914,10.752,'Norway'), 'helsinki':(60.169,24.938,'Finland'),
 'stockholm':(59.329,18.069,'Sweden'), 'copenhagen':(55.676,12.568,'Denmark'),
 'tokyo':(35.676,139.650,'Japan'), 'kyoto':(35.012,135.768,'Japan'),
 'beijing':(39.904,116.407,'China'), 'shanghai':(31.230,121.474,'China'),
 'hong kong':(22.319,114.169,'Hong Kong'), 'singapore':(1.352,103.820,'Singapore'),
 'taipei':(25.033,121.565,'Taiwan'), 'seoul':(37.567,126.978,'South Korea'),
 'bengaluru':(12.972,77.595,'India'), 'bangalore':(12.972,77.595,'India'),
 'delhi':(28.614,77.209,'India'), 'mumbai':(19.076,72.878,'India'),
 'sydney':(-33.869,151.209,'Australia'), 'melbourne':(-37.814,144.963,'Australia'),
 'brisbane':(-27.470,153.026,'Australia'), 'adelaide':(-34.929,138.601,'Australia'),
 'perth':(-31.953,115.861,'Australia'), 'auckland':(-36.849,174.763,'New Zealand'),
 'wellington':(-41.286,174.776,'New Zealand'), 'cape town':(-33.925,18.424,'South Africa'),
 'johannesburg':(-26.204,28.047,'South Africa'), 'nairobi':(-1.292,36.822,'Kenya'),
 'accra':(5.603,-0.187,'Ghana'), 'cairo':(30.044,31.236,'Egypt')
}
HOST_LOCKS, ROBOTS = {}, {}
GUARD = threading.Lock()
DISCOVERED = []

def clean(x):
    value=str(x or '')
    value=BeautifulSoup(value,'html.parser').get_text(' ',strip=True) if '<' in value else html.unescape(value)
    return re.sub(r'\s+', ' ',value).strip()

def safe_url(url):
    """All submitted URLs must be public HTTPS, including every redirect target."""
    p = urlparse(url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:
        raise ValueError('Not a public HTTP(S) URL')
    if p.port not in (None,80,443): raise ValueError('Nonstandard port')
    try:
        addresses=socket.getaddrinfo(p.hostname, p.port or 443)
    except socket.gaierror:
        # The development HTTP proxy resolves public hosts remotely. Restrict this
        # path to the reviewed registry; production Actions performs DNS validation.
        reviewed={urlparse(s['url']).hostname for s in json.loads((ROOT/'data/sources.json').read_text())}
        reviewed.update({'ics.teamup.com','calendar.google.com'})
        if not (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')) or p.hostname.removeprefix('www.') not in {h.removeprefix('www.') for h in reviewed}:raise
        addresses=[]
    for info in addresses:
        if not ipaddress.ip_address(info[4][0]).is_global: raise ValueError('Nonpublic address')
    return url

def get(url, *, robots=True):
    safe_url(url)
    host = urlparse(url).netloc
    with GUARD: lock = HOST_LOCKS.setdefault(host, threading.Lock())
    with lock:
        if robots and host not in ROBOTS:
            rp = RobotFileParser()
            try:
                r = requests.get(urlparse(url).scheme+'://'+host+'/robots.txt',headers={'User-Agent':UA},timeout=10,allow_redirects=False)
                if r.status_code==200: rp.parse(r.text.splitlines()); ROBOTS[host]=rp
                elif r.status_code in (401,403): raise ValueError('Robots access restricted')
                else: ROBOTS[host]=None
            except requests.RequestException: ROBOTS[host]=None
        if robots and ROBOTS.get(host) and not ROBOTS[host].can_fetch(UA,url): raise ValueError('Disallowed by robots.txt')
        for _ in range(6):
            r=requests.get(url,headers={'User-Agent':UA},timeout=(10,20),allow_redirects=False,stream=True)
            if r.is_redirect:
                url=safe_url(urljoin(url,r.headers['Location']));continue
            r.raise_for_status()
            body=bytearray()
            for chunk in r.iter_content(65536):
                body.extend(chunk)
                if len(body)>5_000_000: raise ValueError('Source exceeds 5 MB limit')
            encoding=r.encoding if r.encoding and r.encoding.lower()!='iso-8859-1' else 'utf-8'
            return body.decode(encoding,errors='replace'),url
        raise ValueError('Too many redirects')

def dt_value(value, tz=None):
    if isinstance(value, datetime): d=value
    elif isinstance(value,date):return value.isoformat(),True,None
    elif re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(value)):return str(value),True,None
    else:d=isoparse(str(value))
    if d.tzinfo is None and tz: d=d.replace(tzinfo=ZoneInfo(tz))
    return d.isoformat(),False,str(d.tzinfo) if d.tzinfo else None

def normalise(raw,source,url):
    if not raw.get('title') or not raw.get('start'):return None
    title=clean(raw['title'])[:300]
    if len(title.strip(' ()'))<4:return None
    start,all_day,tz=dt_value(raw['start'],raw.get('timezone') or source.get('timezone'))
    end=dt_value(raw['end'],raw.get('timezone') or source.get('timezone'))[0] if raw.get('end') else None
    start_day=date.fromisoformat(start[:10]);end_day=date.fromisoformat((end or start)[:10])
    if end_day<WINDOW_START.date() or start_day>WINDOW_END.date():return None
    loc=clean(raw.get('location'))[:500]
    desc=clean(raw.get('description'))
    online=bool(re.search(r'\bonline\b|\bzoom\b|virtual|webinar|teams\.microsoft|meet\.google',loc,re.I))
    virtual=raw.get('virtual',False)
    fmt=raw.get('format') or ('hybrid' if (virtual and loc and not online) else 'online' if online or virtual else 'in-person' if loc and not re.search(r'\btbc\b|to be|TBA',loc,re.I) else 'unknown')
    lat=raw.get('lat');lon=raw.get('lon');country=clean(raw.get('country'))
    precision='published' if lat is not None and lon is not None else None
    if fmt in ('in-person','hybrid') and lat is None:
        for city,coords in sorted(CITIES.items(),key=lambda x:-len(x[0])):
            if re.search(r'(?<!\w)'+re.escape(city)+r'(?!\w)',loc,re.I):
                lat,lon,matched_country=coords;country=country or matched_country;precision='city';break
    if fmt=='online':lat=lon=None;country=''
    if not country:
        for c in set(x[2] for x in CITIES.values()):
            if c.lower() in loc.lower():country=c;break
    topics=list(source.get('topics',['systems']))
    for key,pattern in [('cybernetics',r'cybernet|kybernet|vsm\b|stafford beer'),('complexity',r'complex|emergence'),('system-dynamics',r'system dynamics|stock.and.flow'),('systemic-design',r'systemic design|\bRSD\d')]:
        if re.search(pattern,title+' '+desc,re.I) and key not in topics: topics.append(key)
    link=raw.get('url') or url
    if urlparse(link).scheme not in ('http','https'):link=url
    base_uid=str(raw.get('uid') or link)
    occurrence=str(raw.get('recurrenceId') or '')
    uid=hashlib.sha256((source['id']+'|'+base_uid+'|'+occurrence).encode()).hexdigest()[:24]
    notes=list(raw.get('notes',[]))
    if not all_day and not tz: notes.append('Time zone not published; omitted from calendar feeds until confirmed.')
    if all_day: notes.append('Date-only listing; check the organiser for session times.')
    if end and end<start and len(end)==len(start):notes.append('Source end precedes start; end omitted.');end=None
    return dict(id=uid,title=title,start=start,end=end,allDay=all_day,timezone=raw.get('timezone') or source.get('timezone') or tz,
        location=loc or 'Location not published',country=country,latitude=lat,longitude=lon,locationPrecision=precision,format=fmt,
        organiser=clean(raw.get('organiser')) or source['name'],organisationIds=[source['id']],topics=topics,
        description=desc[:400],url=link,sources=[{'id':source['id'],'name':source['name'],'url':url}],
        status='cancelled' if 'cancel' in str(raw.get('status','')).lower() else 'scheduled',language=clean(raw.get('language')) or 'Not specified',
        price=clean(raw.get('price')) or 'See organiser',access=clean(raw.get('access')) or 'See organiser',notes=notes,
        lastSeen=STAMP,sourceUid=base_uid,recurrenceId=occurrence,stale=False,calendarEligible=all_day or bool(tz))

def parse_ics(text,source,url):
    cal=Calendar.from_ical(text)
    raw_events=recurring_ical_events.of(cal,skip_bad_series=True).between(WINDOW_START,WINDOW_END)
    # Cancelled overrides must remain in subscriptions even if an expansion library omits them.
    seen={(str(e.get('UID')),str(e.get('RECURRENCE-ID'))) for e in raw_events}
    for e in cal.walk('VEVENT'):
        if str(e.get('STATUS','')).upper()=='CANCELLED' and (str(e.get('UID')),str(e.get('RECURRENCE-ID'))) not in seen:raw_events.append(e)
    out=[]
    for e in raw_events:
        if not e.get('DTSTART'):continue
        categories=clean(e.get('CATEGORIES'))
        title=str(e.get('SUMMARY','')).strip()
        if not title.strip(' ()'):continue
        desc=str(e.get('DESCRIPTION',''));loc=str(e.get('LOCATION',''))
        org=str(e.get('X-TEAMUP-WHO',''))
        if 'Metaphorum' in categories:org='Metaphorum'
        if re.search('ISSS|International Society for the Systems Sciences',title,re.I):org='ISSS'
        if re.search('Cybernetics Live',title,re.I):org='The Cybernetics Society (CybSoc)'
        raw=dict(uid=str(e.get('UID')),title=title,start=e.decoded('DTSTART'),end=e.decoded('DTEND') if e.get('DTEND') else None,
            description=desc,location=loc,url=str(e.get('URL') or url),organiser=org,status=str(e.get('STATUS','')),
            recurrenceId=str(e.decoded('RECURRENCE-ID')) if e.get('RECURRENCE-ID') else '',
            timezone=str(e.get('DTSTART').params.get('TZID') or cal.get('X-WR-TIMEZONE') or '') or None)
        if loc and not re.search('online|zoom',loc,re.I) and re.search('livestream|hybrid',desc,re.I):raw['format']='hybrid'
        n=normalise(raw,source,url)
        if n:out.append(n)
    return out

def walk_json(obj):
    if isinstance(obj,list):
        for x in obj:yield from walk_json(x)
    elif isinstance(obj,dict):
        typ=obj.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
        if any(x=='Event' or x.endswith('Event') for x in typ):yield obj
        for x in obj.values():
            if isinstance(x,(dict,list)):yield from walk_json(x)

def json_event(e,source,url):
    locs=e.get('location') or [];locs=[locs] if not isinstance(locs,list) else locs
    places=[];virtual=False;geo={};country=''
    for loc in locs:
        if isinstance(loc,str):places.append(loc);continue
        if not isinstance(loc,dict):continue
        if loc.get('@type')=='VirtualLocation':virtual=True;continue
        address=loc.get('address') or {}
        if isinstance(address,str):places.append(clean(loc.get('name'))+' '+address)
        else:
            c=address.get('addressCountry') or '';c=c.get('name','') if isinstance(c,dict) else c
            country=c or country
            places.append(', '.join(str(x) for x in [loc.get('name'),address.get('streetAddress'),address.get('addressLocality'),address.get('addressRegion'),c] if x))
        geo=loc.get('geo') or geo
    mode=str(e.get('eventAttendanceMode',''))
    virtual=virtual or 'Online' in mode or 'Mixed' in mode
    org=e.get('organizer') or {};org=org[0] if isinstance(org,list) and org else org
    offer=e.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
    return normalise(dict(title=e.get('name'),uid=e.get('@id') or e.get('url') or url,start=e.get('startDate'),end=e.get('endDate'),
       description=e.get('description'),location='; '.join(places),country=country,lat=geo.get('latitude'),lon=geo.get('longitude'),
       virtual=virtual,organiser=org.get('name') if isinstance(org,dict) else org,url=e.get('url') or url,status=e.get('eventStatus'),
       language=e.get('inLanguage'),price=(str(offer.get('price'))+' '+str(offer.get('priceCurrency',''))) if isinstance(offer,dict) and offer.get('price') is not None else None),source,url)

def parse_scio(soup,source,url):
    events=[]
    for article in soup.select('article.node--type-event, article.node--type-course'):
        card=article.select_one('.card-view') or article
        def tx(sel):
            el=card.select_one(sel);return el.get_text(' ',strip=True) if el else ''
        a=card.select_one('a.title-link');dates=tx('.event-date .fw-600');times=tx('.event-date .fw-200')
        if not a or not dates:continue
        ds=re.split(r'\s+-\s+',dates);ds=[re.sub(r'(\d+)(st|nd|rd|th)',r'\1',d) for d in ds]
        try:
            start=parse(ds[0]).date();end=parse(ds[-1]).date()
            org=tx('.event-organiser');tz='Europe/London'
            if any(x in org for x in ['DACH','Belgium','NL','Polska']):tz={'Polska':'Europe/Warsaw','NL':'Europe/Amsterdam','Belgium':'Europe/Brussels','DACH':'Europe/Berlin'}[next(x for x in ['Polska','NL','Belgium','DACH'] if x in org)]
            ts=re.findall(r'\d{1,2}:\d{2}',times)
            if len(ts)>=2:
                start=datetime.combine(start,datetime.strptime(ts[0],'%H:%M').time(),ZoneInfo(tz));end=datetime.combine(end,datetime.strptime(ts[-1],'%H:%M').time(),ZoneInfo(tz))
            else:end+=timedelta(days=1)
            title=clean(a.get_text(' ',strip=True));notes=[]
            years=re.findall(r'\b20\d{2}\b',title)
            if years and str(start.year) not in years:notes.append('Title year differs from the published date. Check with the organiser.')
            loc=tx('.event-location')
            n=normalise(dict(title=title,start=start,end=end,location=loc,organiser=org,timezone=tz,url=urljoin(url,a['href']),price=tx('.price'),language=tx('.languages-tag'),access=tx('.book-now-button .small-text'),notes=notes),source,urljoin(url,a['href']))
            if n:events.append(n)
        except (ValueError,TypeError):continue
    return events

def parse_isss_lab(soup,source,url):
    events=[]
    # Google Sites renders each event title in a heading followed by a dated paragraph.
    for h in soup.select('h2,h3'):
        title=h.get_text(' ',strip=True)
        if not re.search(r'20\d\d',title):continue
        texts=[]
        for el in h.next_elements:
            if getattr(el,'name',None) in ['h2','h3']:break
            if getattr(el,'name',None)=='p':texts.append(el.get_text(' ',strip=True))
        text=' '.join(texts)
        m=re.search(r'([A-Z][a-z]{2} \d{1,2}, 20\d{2} \d{1,2}:\d{2} [AP]M) Eastern',text)
        if not m:continue
        raw=dict(title=title,start=parse(m[1]).replace(tzinfo=ZoneInfo('America/New_York')),location='Online',organiser='ISSS',url=url,uid=title,access='Members / see organiser')
        # Board meetings are organisational business, not public events.
        if 'Board of Directors Meeting' in title:continue
        n=normalise(raw,source,url)
        if n:events.append(n)
    return events

def parse_asc(soup,source,url):
    out=[]
    for block in soup.select('span.information'):
        h=block.select_one('h2');p=block.select_one('p');a=block.select_one('a[href]')
        if not h or not p or not a:continue
        text=p.get_text(' ',strip=True)
        m=re.search(r'((?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), [A-Z][a-z]+ \d{1,2}, 20\d{2})\s*\|\s*(\d{1,2}(?::\d{2})? [AP]M) ED[ST]',text)
        if not m:continue
        d=parse(m[1]+' '+m[2]).replace(tzinfo=ZoneInfo('America/New_York'))
        n=normalise(dict(title=h.get_text(' ',strip=True),start=d,location='Online',organiser='American Society for Cybernetics (ASC)',url=urljoin(url,a['href']),timezone='America/New_York'),source,urljoin(url,a['href']))
        if n:out.append(n)
    return out

def parse_cecan(soup,source,url):
    out=[]
    for card in soup.select('.postlist'):
        h=card.select_one('h3 a');meta=card.select_one('.newsdate');a=card.select_one('a[title]')
        if not h or not meta:continue
        t=meta.get_text(' ',strip=True);m=re.search(r'(\d{1,2} [A-Z][a-z]+ 20\d{2})',t)
        if not m:continue
        d=parse(m[1]).date();tm=re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|noon))',t,re.I)
        if tm:
            ts=tm[1].replace('noon','pm');d=datetime.combine(d,parse(ts).time(),ZoneInfo('Europe/London'))
        n=normalise(dict(title=a.get('title') if a else h.get_text(' ',strip=True),start=d,location='Online' if 'online' in t.lower() else '',url=urljoin(url,h['href'])),source,urljoin(url,h['href']))
        if n:out.append(n)
    return out

def parse_css(soup,source,url):
    t=soup.get_text(' ',strip=True);h=soup.select_one('h1')
    start=re.search(r'Starts On\s+(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})',t)
    end=re.search(r'Ends On\s+(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})',t)
    if not h or not start:return []
    loc=re.search(r'Location:\s*(.*?)\s*(?:Contact Email:|Website:|$)',t)
    venue=re.search(r'Venue:\s*(.*?)\s*Location:',t)
    location=', '.join(x.group(1) for x in [venue,loc] if x and x.group(1) not in ['None',''])
    n=normalise(dict(title=h.get_text(' ',strip=True),start=parse(start[1]).date(),end=parse(end[1]).date()+timedelta(days=1) if end else None,location=location,url=url),source,url)
    return [n] if n else []

def find_feeds(soup,url):
    feeds=[]
    for el in soup.select('a[href],link[href],iframe[src]'):
        link=urljoin(url,el.get('href') or el.get('src') or '')
        if urlparse(link).scheme in ('http','https') and re.search(r'\.ics(?:\?|$)|[?&]ical=1|format=ical',link,re.I):feeds.append(link)
        if 'teamup.com/' in link and '/feed/' not in link:
            m=re.search(r'teamup\.com/(ks[a-zA-Z0-9]+)',link)
            if m:feeds.append('https://ics.teamup.com/feed/'+m[1]+'/0.ics')
        if 'calendar.google.com/calendar/embed' in link:
            for cid in parse_qs(urlparse(link).query).get('src',[]):feeds.append('https://calendar.google.com/calendar/ical/'+quote(cid,safe='')+'/public/basic.ics')
    return list(dict.fromkeys(feeds))[:8]

def event_links(soup,url):
    links=[];host=urlparse(url).hostname
    for a in soup.select('a[href]'):
        link=urljoin(url,a['href']);p=urlparse(link);label=a.get_text(' ',strip=True)
        if p.scheme not in ('http','https') or p.fragment:continue
        if p.hostname!=host:
            if re.search(r'calendar|events|conference|symposium',label,re.I) and len(label)>6:
                with GUARD:DISCOVERED.append({'name':label[:140],'url':link,'foundOn':url,'checkedAt':STAMP})
            continue
        if re.search(r'/event[s]?/[^/]+|/20\d\d/|conference|symposium|webinar|seminar|workshop',p.path,re.I) and not re.search(r'\.(pdf|jpg|png|svg|ics)$|/tag/|/category/|/wp-content/|/past|/feed',p.path,re.I) and link.rstrip('/')!=url.rstrip('/'):
            links.append(link)
    return list(dict.fromkeys(links))[:16]

def collect_source(source):
    report={**source,'checkedAt':STAMP,'status':'ok','message':'','events':0,'feedsFound':[],'pagesChecked':0}
    events=[];errors=[];successful=0
    try:
        text,url=get(source['url']);soup=BeautifulSoup(text,'html.parser');successful+=1;report['pagesChecked']+=1
        if text.lstrip().startswith('BEGIN:VCALENDAR'):
            events+=parse_ics(text,source,url)
        # Detect explicit parked/reassigned domains, never import unrelated pages.
        if re.search(r'casino|slot gacor|togel|buy this domain',soup.title.get_text() if soup.title else '',re.I):raise ValueError('Domain appears unrelated to this organisation; review needed')
        if source['adapter']=='scio':events+=parse_scio(soup,source,url)
        elif source['adapter']=='isss_lab':events+=parse_isss_lab(soup,source,url)
        elif source['adapter']=='asc':events+=parse_asc(soup,source,url)
        elif source['adapter']=='cecan':events+=parse_cecan(soup,source,url)
        feeds=list(dict.fromkeys(source.get('feeds',[])+([] if source.get('feedsExclusive') else find_feeds(soup,url))))
        report['feedsFound']=feeds
        for feed in feeds:
            try:
                txt,final=get(feed);events+=parse_ics(txt,source,final);successful+=1
            except Exception as e:errors.append('Feed: '+str(e)[:180])
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                for e in walk_json(json.loads(script.string or script.get_text())):
                    n=json_event(e,source,url)
                    if n:events.append(n)
            except (ValueError,TypeError,AttributeError):continue
        if source['adapter'] in ('auto','css'):
            for link in event_links(soup,url):
                try:
                    txt,final=get(link);ss=BeautifulSoup(txt,'html.parser');report['pagesChecked']+=1
                    if source['adapter']=='css':events+=parse_css(ss,source,final)
                    for script in ss.select('script[type="application/ld+json"]'):
                        try:
                            for e in walk_json(json.loads(script.string or script.get_text())):
                                n=json_event(e,source,final)
                                if n:events.append(n)
                        except (ValueError,TypeError,AttributeError):continue
                except Exception as e:errors.append('Page: '+str(e)[:150])
    except Exception as e:
        report['status']='failed';errors.append(str(e)[:220])
        # Explicit public feeds are independent of the landing page's availability.
        for feed in source.get('feeds',[]):
            try:
                txt,final=get(feed);events+=parse_ics(txt,source,final);successful+=1
                report['feedsFound'].append(feed)
            except Exception as e:errors.append('Feed: '+str(e)[:160])
    unique={e['id']:e for e in events};events=list(unique.values())
    report['events']=len(events)
    if events:report['status']='partial' if errors else 'ok';report['message']='Collecting dated events'+('; some pages or feeds failed' if errors else '')
    elif successful and report['status']!='failed':report['status']='needs-review';report['message']='No dated events extracted; a working page is not proof of complete coverage'
    else:report['message']='Source could not be collected'
    report['errors']=errors[:5]
    print(f"{source['id']}: {report['status']} · {len(events)} events · {report['pagesChecked']} pages",flush=True)
    return events,report

def deduplicate(events,previous):
    old_by_id={e['id']:e for e in previous};merged={};by_url={};by_title={}
    for e in sorted(events,key=lambda x:(x['sources'][0]['id']=='community',x['start'])):
        key=(e['url'].rstrip('/'),e['start'][:10],e.get('recurrenceId',''))
        title=(re.sub(r'[^\w]','',e['title'].casefold()),e['start'][:10])
        match=by_url.get(key) or by_title.get(title)
        if match:
            m=merged[match]
            for s in e['sources']:
                if s not in m['sources']:m['sources'].append(s)
            m['topics']=sorted(set(m['topics']+e['topics']));m['organisationIds']=sorted(set(m['organisationIds']+e['organisationIds']))
            continue
        merged[e['id']]=e;by_url[key]=e['id'];by_title[title]=e['id']
    for e in merged.values():
        old=old_by_id.get(e['id'])
        # Prefer the existing subscription UID if a duplicate is now collected by a new source.
        if not old:
            old=next((x for x in previous if x['url'].rstrip('/')==e['url'].rstrip('/') and x.get('recurrenceId','')==e.get('recurrenceId','')),None)
            if old:e['id']=old['id']
        fields=['title','start','end','status','location','url','description','notes']
        changed=not old or any(e.get(k)!=old.get(k) for k in fields)
        # Classify a society named in a shared calendar without attributing the
        # entire community calendar to the host society.
        for oid,pat in [('isss',r'\bISSS\b|International Society for the Systems Sciences'),('cybsoc',r'Cybernetics Society|Cybernetics Live'),('metaphorum',r'Metaphorum'),('rsd',r'\bRSD\d|Systemic Design Association')]:
            if re.search(pat,e['organiser']+' '+e['title'],re.I) and oid not in e['organisationIds']:e['organisationIds'].append(oid)
        e['sequence']=(old.get('sequence',0)+1 if old else 0) if changed else old.get('sequence',0)
        e['updatedAt']=STAMP if changed else old.get('updatedAt',STAMP)
        e['firstSeen']=old.get('firstSeen',STAMP) if old else STAMP
    return sorted(merged.values(),key=lambda x:(x['start'],x['title']))

def make_calendar(events,name):
    c=Calendar();c.add('prodid','-//Systems Events Map//EN');c.add('version','2.0');c.add('calscale','GREGORIAN')
    c.add('x-wr-calname',name);c.add('x-published-ttl','PT24H');c.add('refresh-interval',timedelta(hours=24))
    for e in events:
        if not e.get('calendarEligible',True):continue
        v=Event();v.add('uid',e['id']+'@systemsmap.antlerboy.com');v.add('summary',e['title'])
        for field,key in [('dtstart','start'),('dtend','end')]:
            if not e.get(key):continue
            d=date.fromisoformat(e[key]) if e['allDay'] else isoparse(e[key]).astimezone(timezone.utc)
            v.add(field,d)
        v.add('dtstamp',isoparse(e.get('updatedAt',STAMP)));v.add('last-modified',isoparse(e.get('updatedAt',STAMP)));v.add('sequence',e.get('sequence',0))
        v.add('url',e['url']);v.add('location',e['location']);v.add('categories',[TOPICS[t] for t in e['topics'] if t in TOPICS])
        notes='\n'.join(e.get('notes',[]))
        if e.get('stale'):notes+='\nThis event could not be rechecked on the latest collection. Confirm with the organiser.'
        v.add('description',f"{e['organiser']}\n{e['description']}\n{e['url']}\n{notes}".strip())
        v.add('status','CANCELLED' if e['status']=='cancelled' else 'CONFIRMED');v.add('transp','TRANSPARENT')
        c.add_component(v)
    return c.to_ical()

def main():
    sources=json.loads((ROOT/'data/sources.json').read_text())
    oldpath=ROOT/'dist/data/events.json';previous=json.loads(oldpath.read_text()).get('events',[]) if oldpath.exists() else []
    events=[];reports=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for ev,report in executor.map(collect_source,sources):events+=ev;reports.append(report)
    found={e['id'] for e in events};status={s['id']:s['status'] for s in reports}
    for old in previous:
        if old['id'] in found or (old.get('end') or old['start'])[:10]<WINDOW_START.date().isoformat():continue
        # Keep missing future listings visible; distinguish explicit cancellation from disappearance.
        old['stale']=True
        note='No longer found in the latest source listing; confirmation needed.' if all(status.get(s['id'])=='ok' for s in old['sources']) else 'Source could not be fully rechecked.'
        old['notes']=list(dict.fromkeys(old.get('notes',[])+[note]));events.append(old)
    overrides=ROOT/'data/approved-events.json'
    if overrides.exists():
        for raw in json.loads(overrides.read_text()):
            s={'id':'community-submissions','name':raw.get('organiser','Community submission'),'topics':raw.get('topics',['systems']),'timezone':raw.get('timezone')}
            n=normalise(raw,s,raw['url'])
            if n:events.append(n)
    events=deduplicate(events,previous)
    data={'generatedAt':STAMP,'windowStart':WINDOW_START.date().isoformat(),'windowEnd':WINDOW_END.date().isoformat(),'events':events}
    dest=ROOT/'dist/data';dest.mkdir(parents=True,exist_ok=True)
    (dest/'events.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (dest/'sources.json').write_text(json.dumps({'checkedAt':STAMP,'sources':reports},ensure_ascii=False,indent=2)+'\n')
    feeds=ROOT/'dist/feeds';feeds.mkdir(exist_ok=True)
    groups={'all':('All systems, cybernetics, and complexity events',events),'online':('Online events',[e for e in events if e['format'] in ['online','hybrid']])}
    groups.update({'topic-'+k:(v,[e for e in events if k in e['topics']]) for k,v in TOPICS.items()})
    groups.update({'org-'+s['id']:(s['name'],[e for e in events if s['id'] in e['organisationIds']]) for s in sources})
    for f in feeds.glob('*.ics'):
        if f.stem not in groups:f.unlink()
    for k,(name,es) in groups.items():(feeds/(k+'.ics')).write_bytes(make_calendar(es,name))
    (dest/'feeds.json').write_text(json.dumps([{'id':k,'name':v[0],'events':len(v[1])} for k,v in groups.items()],ensure_ascii=False,indent=2)+'\n')
    discoveries=list({x['url']:x for x in DISCOVERED}.values())
    (ROOT/'data/discovered-sources.json').write_text(json.dumps(discoveries,ensure_ascii=False,indent=2)+'\n')
    summary={'checkedAt':STAMP,'events':len(events),'upcoming':sum((e.get('end') or e['start'])[:10]>=NOW.date().isoformat() for e in events),'sources':len(reports),'collecting':sum(s['events']>0 for s in reports),'failed':sum(s['status']=='failed' for s in reports)}
    (dest/'health.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
    if not events:raise SystemExit('No events available. Refusing an empty publication.')

if __name__=='__main__':main()
