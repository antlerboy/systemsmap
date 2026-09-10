import sys,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect,extract_submission,accept_submission
from bs4 import BeautifulSoup
from icalendar import Calendar
SOURCE={'id':'scio','name':'SCiO','topics':['systems']}
class SubmissionTests(unittest.TestCase):
    def test_polish_online_focus_keeps_access_and_no_venue(self):
        e=collect.normalise(dict(title='Polish systems meeting',start='2026-09-15T18:00:00+02:00',location='Online',country='Poland',language='Polish',access='All welcome'),SOURCE,'https://example.org/event')
        self.assertEqual(e['audienceCountries'],['Poland']);self.assertEqual(e['country'],'');self.assertIsNone(e['latitude']);self.assertEqual(e['language'],'Polish');self.assertEqual(e['access'],'All welcome')
        self.assertEqual(e['languageRequirement'],'');self.assertEqual(e['interpretation'],'')
        item=Calendar.from_ical(collect.make_calendar([e],'test')).walk('VEVENT')[0]
        self.assertIn('Geographic focus: Poland',str(item['DESCRIPTION']));self.assertIn('Language: Polish',str(item['DESCRIPTION']))
    def test_chapter_focus_is_not_inferred_from_language(self):
        self.assertEqual(collect.chapter_focus('SCiO Polska'),(['Poland'],[]))
        self.assertEqual(collect.chapter_focus('SCiO DACH'),(['Germany','Austria','Switzerland'],['DACH']))
        e=collect.normalise(dict(title='English systems meeting',start='2026-09-15',location='Online',language='English'),SOURCE,'https://example.org/event')
        self.assertEqual(e['audienceCountries'],[])
    def test_naked_link_and_extracted_event(self):
        data=extract_submission.proposal('https://example.org/event')
        raw={'@type':'Event','name':'A systems event','startDate':'2026-09-15T18:00:00+02:00','endDate':'2026-09-15T19:30:00+02:00','organizer':{'name':'Test organiser'},'eventAttendanceMode':'https://schema.org/OnlineEventAttendanceMode','inLanguage':'Polish'}
        with patch.object(collect,'get',return_value=('<script type="application/ld+json">'+json.dumps(raw)+'</script>',data['url'])):
            parsed,notes=extract_submission.extract(data)
        self.assertEqual(parsed['title'],'A systems event');self.assertEqual(parsed['startTime'],'16:00');self.assertEqual(parsed['timezone'],'UTC');self.assertEqual(parsed['format'],'online');self.assertFalse(notes)
    def test_missing_date_is_not_invented(self):
        with patch.object(collect,'get',return_value=('<h1>Systems gathering</h1><p>See you soon</p>','https://example.org/event')):
            parsed,notes=extract_submission.extract({'kind':'auto','url':'https://example.org/event'})
        self.assertFalse(parsed.get('start'));self.assertTrue(notes)
    def test_scio_detail_page_extracts_published_date_and_details(self):
        html='''<h1>SCiO UK Virtual Development Event - October 2026</h1>
        <div class="event-date"><div class="fw-400">Tue, Oct 6th, 2026</div><div class="fw-200">13:00 - 15:00 GMT+1</div></div>
        <div class="field--name-field-organiser-"><div class="field__item">SCiO UK</div></div>
        <div class="mb-4"><div class="fw-500">Location</div>This is an online event</div>
        <div class="mb-4"><div class="fw-500">Pricing Info</div>FREE to members</div>
        <div class="mb-4"><div class="fw-500">Languages spoken</div>English</div>
        <div class="mb-4"><div class="fw-500">Access</div>Members only</div>'''
        url='https://www.systemspractice.org/events/scio-uk-virtual-development-event-october-2026'
        with patch.object(collect,'get',return_value=(html,url)):
            parsed,notes=extract_submission.extract({'kind':'auto','url':url})
        self.assertFalse(notes);self.assertEqual(parsed['start'],'2026-10-06');self.assertEqual(parsed['startTime'],'13:00')
        self.assertEqual(parsed['timezone'],'Europe/London');self.assertEqual(parsed['organiser'],'SCiO UK')
        self.assertEqual(parsed['format'],'online');self.assertEqual(parsed['access'],'Members only')
    def test_blocked_link_stays_unpublished(self):
        with patch.object(collect,'get',side_effect=ValueError('Disallowed by robots.txt')):
            with self.assertRaisesRegex(ValueError,'Disallowed'):extract_submission.extract({'url':'https://example.org/event'})
    def test_nonpublic_target_rejected(self):
        with patch.object(collect.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaisesRegex(ValueError,'Nonpublic'):collect.safe_url('https://example.org/event')
    def test_manual_review_replaces_stale_duplicate_and_retains_uid(self):
        old=collect.deduplicate([collect.normalise(dict(title='Systems event',start='2026-09-15',location='Online'),SOURCE,'https://example.org/event')],[])
        old[0]['stale']=True
        new=collect.normalise(dict(title='Systems event',start='2026-09-15',location='Online',audienceCountries=['Poland']),{**SOURCE,'id':'community-submissions'},'https://example.org/event')
        merged=collect.deduplicate(old+[new],old)
        self.assertEqual(len(merged),1);self.assertFalse(merged[0]['stale']);self.assertEqual(merged[0]['id'],old[0]['id']);self.assertEqual(merged[0]['audienceCountries'],['Poland'])
    def test_quick_form_only_requires_url(self):
        soup=BeautifulSoup((collect.ROOT/'dist/index.html').read_text(),'html.parser');f=soup.select_one('#submission')
        self.assertEqual([e.get('name') for e in f.select('[required]')],['url']);self.assertIsNotNone(f.select_one('details input[name="languageRequirement"]'))

if __name__=='__main__':unittest.main()
