import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect
from icalendar import Calendar

SOURCE={'id':'test','name':'Test society','topics':['systems'],'timezone':'Europe/London'}
class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.patches=[patch.object(collect,'WINDOW_START',datetime(2026,1,1,tzinfo=timezone.utc)),patch.object(collect,'WINDOW_END',datetime(2027,1,1,tzinfo=timezone.utc))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def test_recurrence_dst_and_cancellation(self):
        raw='''BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:stable-uid\r
DTSTART;TZID=Europe/London:20261018T100000\r
DTEND;TZID=Europe/London:20261018T110000\r
RRULE:FREQ=WEEKLY;COUNT=3\r
SUMMARY:Systems workshop\r
LOCATION:Online\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:stable-uid\r
RECURRENCE-ID;TZID=Europe/London:20261101T100000\r
DTSTART;TZID=Europe/London:20261101T100000\r
DTEND;TZID=Europe/London:20261101T110000\r
STATUS:CANCELLED\r
SUMMARY:Systems workshop\r
LOCATION:Online\r
END:VEVENT\r
END:VCALENDAR\r
'''
        with patch.object(collect,'WINDOW_START',datetime(2026,10,1,tzinfo=timezone.utc)),patch.object(collect,'WINDOW_END',datetime(2026,12,1,tzinfo=timezone.utc)):
            ev=collect.parse_ics(raw,SOURCE,'https://example.org/calendar.ics')
        self.assertEqual(len(ev),3);self.assertEqual(len({e['id'] for e in ev}),3)
        self.assertIn('+01:00',ev[0]['start']);self.assertIn('+00:00',ev[1]['start'])
        self.assertTrue(any(e['status']=='cancelled' for e in ev))
    def test_reschedule_keeps_uid_and_increments_sequence(self):
        raw=dict(title='A systems event',start='2026-10-20T10:00:00+01:00',url='https://example.org/event',uid='original')
        old=collect.deduplicate([collect.normalise(raw,SOURCE,raw['url'])],[])
        raw.update(start='2026-10-21T10:00:00+01:00',title='Updated systems event')
        new=collect.deduplicate([collect.normalise(raw,SOURCE,raw['url'])],old)
        self.assertEqual(old[0]['id'],new[0]['id']);self.assertEqual(new[0]['sequence'],old[0]['sequence']+1)
    def test_unknown_timezone_is_not_silently_utc(self):
        source={k:v for k,v in SOURCE.items() if k!='timezone'}
        e=collect.normalise(dict(title='Unknown timezone',start='2026-10-20T10:00:00',url='https://example.org/event'),source,'https://example.org/event')
        self.assertFalse(e['calendarEligible']);self.assertEqual(len(Calendar.from_ical(collect.make_calendar([e],'Test')).walk('VEVENT')),0)
    def test_all_day_exclusive_end_and_unicode_roundtrip(self):
        e=collect.normalise(dict(title='Cybernétique, São Paulo; systems',start='2026-10-20',end='2026-10-22',location='São Paulo, Brazil',url='https://example.org/event'),SOURCE,'https://example.org/event')
        cal=Calendar.from_ical(collect.make_calendar([e],'Test'));item=cal.walk('VEVENT')[0]
        self.assertEqual(str(item['SUMMARY']),e['title']);self.assertEqual(item.decoded('DTEND').isoformat(),'2026-10-22')
        self.assertEqual(e['country'],'Brazil');self.assertIsNotNone(e['latitude'])
    def test_feed_submission_is_not_an_html_page(self):
        source={**SOURCE,'adapter':'ics','url':'https://example.org/calendar.ics','feeds':['https://example.org/calendar.ics']}
        raw='BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n'
        with patch.object(collect,'get',return_value=(raw,source['url'])):
            ev,report=collect.collect_source(source)
        self.assertEqual(ev,[])

if __name__=='__main__':unittest.main()
