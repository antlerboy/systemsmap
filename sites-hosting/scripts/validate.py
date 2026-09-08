#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import date,datetime
from icalendar import Calendar
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'dist/data/events.json').read_text())
events=data['events'];assert events,'No events'
ids=[e['id'] for e in events];assert len(set(ids))==len(ids),'Duplicate event IDs'
for e in events:
    assert e['title'] and e['url'].startswith(('http://','https://'))
    assert e['sources'] and e['lastSeen']
    start=date.fromisoformat(e['start']) if e['allDay'] else datetime.fromisoformat(e['start'])
    if e['end']:
        end=date.fromisoformat(e['end']) if e['allDay'] else datetime.fromisoformat(e['end'])
        assert end>=start,(e['title'],'end precedes start')
    assert (e['latitude'] is None)==(e['longitude'] is None)
    if e['latitude'] is not None:assert -90<=float(e['latitude'])<=90 and -180<=float(e['longitude'])<=180
    if e['format']=='online':assert e['latitude'] is None
for f in (ROOT/'dist/feeds').glob('*.ics'):
    cal=Calendar.from_ical(f.read_bytes());ev=cal.walk('VEVENT')
    uids=[str(x['UID']) for x in ev];assert len(uids)==len(set(uids)),f
    for item in ev:assert item.get('DTSTART') and item.get('DTSTAMP') and item.get('URL')
for path in ['index.html','app.js','style.css','icon.svg','vendor/leaflet.js','vendor/leaflet.css','vendor/world.geojson']:
    assert (ROOT/'dist'/path).stat().st_size>0,path
for f in json.loads((ROOT/'dist/data/feeds.json').read_text()):assert (ROOT/'dist/feeds'/(f['id']+'.ics')).exists()
print(f'Validated {len(events)} events, {len(list((ROOT/"dist/feeds").glob("*.ics")))} calendar feeds, and site assets.')
