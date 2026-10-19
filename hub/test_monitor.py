import io
import json
import socket
import socketserver
import threading
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from inventory.models import Site
from hub.models import TeamMember, TowerStatus, TowerReading
from hub import licor
from hub.monitor import collect, display_status

DATA='(Data (DiagVal 8191)(CO2MF 418.2)(H2OMF 12.3)(Temp 20.0)(Pres 98.5)(AvgSS 92)(Cooler 1.4)(MeasFlowRate 14.9)(FlowDrive 46)(U 3)(V 4))'
IDENTITY='(EmbeddedSW (Model LI-7200RS)(Version 8.8.36))(Coef (Current (SerialNo 72H-TEST)))'
GOOD=IDENTITY+DATA+'(Diagnostics (SYNC TRUE)(PLL TRUE)(DetOK TRUE)(Chopper TRUE)(Head 1))(Info (USB (State 1)(Size 32000)(Free 20000)))(FlowBox (MeasFlowRate 14.9))'


class LicorProtocolTests(SimpleTestCase):
    def test_real_tcp_exchange_is_read_only_and_closes_the_connection(self):
        sent=[]
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                for line in self.rfile:
                    command=line.decode().strip()
                    sent.append(command)
                    if command=="(Data ?)":
                        self.wfile.write(GOOD.encode()+b"\n")
                    else:
                        self.wfile.write(b"(Error (Received TRUE))\n")
                    self.wfile.flush()
        with socketserver.TCPServer(("127.0.0.1",0),Handler) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                result=licor.poll("127.0.0.1",server.server_address[1],timeout=1)
                self.assertTrue(result["has_data"])
                self.assertEqual(sent,list(licor.QUERIES))
            finally:
                server.shutdown();thread.join(timeout=2)
    def test_guard_accepts_only_fixed_read_queries(self):
        for query in licor.QUERIES:
            self.assertEqual(licor.read_only_query(query),(query+"\n").encode("ascii"))
        for query in ['(Outputs(BW 10))','(Calibrate(ZeroCO2(Date "now")))','(Program(Reset TRUE))','(Data ?)(Program(Reset TRUE))','(Network ?)','(Data ?)\n(Outputs(BW 10))', '(Data ? extra)', '']:
            with self.assertRaises(ValueError,msg=query):licor.read_only_query(query)

    def test_parser_handles_quotes_split_concatenated_and_case_sensitive_tags(self):
        chunks=['(Data (Temp 20)(TEMP 18))','(Calibrate (ZeroCO2 (Date "26 08 2009 10:37")))']
        records,remainder=licor.split_records(''.join(chunks)+'(Data (CO2MF 4')
        self.assertEqual(records,chunks);self.assertEqual(remainder,'(Data (CO2MF 4')
        self.assertEqual(licor.flatten(licor.parse(chunks[0])),{"Data/Temp":"20","Data/TEMP":"18"})
        with self.assertRaises(ValueError):licor.parse('(Data ?)(Outputs(BW 10))')
        with self.assertRaises(ValueError):licor.parse('(Data (CO2MF 4)')

    def test_known_diagnostic_words_match_ec_monitor(self):
        for model,word in [('LI-7500DS',125),('LI-7200RS',8061)]:
            result=licor.decode([f'(EmbeddedSW (Model {model}))',f'(Data (DiagVal {word})(CO2MF 418))'])
            failed=[f["label"] for f in result["flags"] if f["ok"] is False]
            self.assertEqual(failed,["Chopper"])
            self.assertAlmostEqual(next(m["value"] for m in result["metrics"] if m["tag"]=="AvgSS"),86.71)

    def test_healthy_values_and_wind_speed(self):
        records,_=licor.split_records(GOOD)
        result=licor.decode(records)
        self.assertEqual(result["status"],"healthy",result["issues"])
        self.assertEqual(result["serial"],"72H-TEST")
        self.assertEqual(next(m["value"] for m in result["metrics"] if m["tag"]=="WindSpeed"),5)

    def test_low_flow_dirty_optics_and_usb_fault_are_ranked(self):
        records,_=licor.split_records(GOOD.replace('(MeasFlowRate 14.9)','(MeasFlowRate 0)').replace('(AvgSS 92)','(AvgSS 20)').replace('(State 1)','(State 3)'))
        result=licor.decode(records)
        self.assertEqual(result["status"],"fault")
        self.assertIn("No analyzer flow",[i["title"] for i in result["issues"]])
        self.assertIn("Logging drive error",[i["title"] for i in result["issues"]])

    def test_no_measurement_is_not_healthy_and_network_details_are_not_exposed(self):
        result=licor.decode(['(Network (IP (Address 10.20.30.40)(Password secret)))',IDENTITY])
        self.assertFalse(result["has_data"])
        self.assertNotEqual(result["status"],"healthy")
        self.assertNotIn('10.20.30.40',json.dumps(result));self.assertNotIn('secret',json.dumps(result))

    def test_labelless_values_are_inferred_without_changing_output_configuration(self):
        outputs='(Outputs (ENet (Ndx TRUE)(DiagVal TRUE)(CO2Raw TRUE)(CO2D TRUE)(H2ORaw TRUE)(H2OD TRUE)(Temp TRUE)(Pres TRUE)(Aux TRUE)(Cooler TRUE)))'
        result=licor.decode([outputs],['252 250 0.15401 32.2167 0.03569 196.703 24.33 98.6 0 1.5730'])
        self.assertTrue(result["has_data"])
        self.assertTrue(any('Label-less' in i["title"] for i in result["issues"]))

    def test_socket_client_sends_only_guarded_queries_and_handles_split_reads(self):
        fake=MagicMock()
        fake.__enter__.return_value=fake
        fake.recv.side_effect=[GOOD[:35].encode(),GOOD[35:100].encode(),GOOD[100:].encode(),b'']
        with patch('hub.licor.socket.create_connection',return_value=fake):
            result=licor.poll('private-tower',7200,1)
        self.assertTrue(result["has_data"])
        self.assertEqual([call.args[0] for call in fake.sendall.call_args_list],[licor.read_only_query(q) for q in licor.QUERIES])


class MonitorAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site=Site.objects.create(code='UQAM_3',name='Bog',amp='CA-CQ3',location='Quebec',description='Bog',date_activated='2025-04-10')
        cls.other=Site.objects.create(code='UQAM_2',name='Other',amp='CA-CQ2',location='Quebec',description='Bog',date_activated='2025-04-10')
        cls.viewer=get_user_model().objects.create_user('monitor-viewer')
        TeamMember.objects.create(user=cls.viewer,role='viewer')
    def setUp(self):
        self.client=APIClient();self.client.force_authenticate(self.viewer)
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.config=Path(self.folder.name)/'private.json'
        self.config.write_text(json.dumps({'UQAM_3':{'host':'private-tower.invalid','port':7200,'username':'private-user','password':'do-not-disclose'}}))
        self.override=override_settings(MONITOR_STATIONS_FILE=str(self.config));self.override.enable();self.addCleanup(self.override.disable)
    def test_api_is_authenticated_site_scoped_and_has_no_write_methods(self):
        self.viewer.team_member.sites.add(self.site)
        self.assertEqual(self.client.get(f'/api/monitor/?site={self.other.pk}').status_code,403)
        for method in [self.client.post,self.client.patch,self.client.delete]:
            self.assertEqual(method('/api/monitor/',{'command':'(Program(Reset TRUE))'},format='json').status_code,405)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/monitor/').status_code,403)
    @patch('hub.monitor.licor.poll')
    def test_check_all_and_individual_return_metrics_without_secrets(self,poll):
        poll.return_value=licor.decode(licor.split_records(GOOD)[0])
        response=self.client.get('/api/monitor/?refresh=1')
        self.assertEqual(response.status_code,200)
        output=json.dumps(response.data,default=str)
        for secret in ['private-tower.invalid','do-not-disclose','private-user',str(self.config)]:self.assertNotIn(secret,output)
        bycode={t['code']:t for t in response.data['towers']}
        self.assertEqual(bycode['UQAM_3']['status'],'healthy')
        self.assertEqual(bycode['UQAM_2']['status'],'not_configured')
        self.assertEqual(TowerReading.objects.count(),1)
        individual=self.client.get(f'/api/monitor/?site={self.site.pk}&refresh=1')
        self.assertEqual(len(individual.data['towers']),1)
        self.assertEqual(len(individual.data['towers'][0]['history']),1)
        self.assertEqual(poll.call_count,1) # Shared cooldown also applies to individual checks.
    @patch('hub.monitor.licor.poll')
    def test_failure_preserves_last_values_with_unreachable_status(self,poll):
        payload=licor.decode(licor.split_records(GOOD)[0])
        obj=TowerStatus.objects.create(site=self.site,status='healthy',observed_at=timezone.now()-timedelta(minutes=10),payload=payload,last_good=payload)
        poll.side_effect=OSError('private-tower.invalid password=do-not-disclose')
        collect([self.site])
        obj.refresh_from_db();state=display_status(self.site,obj)
        self.assertEqual(state['status'],'unreachable');self.assertTrue(state['stale']);self.assertTrue(state['last_known'])
        self.assertTrue(state['data']['metrics'])
        self.assertNotIn('do-not-disclose',json.dumps(state,default=str))
    def test_old_healthy_reading_becomes_stale(self):
        obj=TowerStatus.objects.create(site=self.site,status='healthy',observed_at=timezone.now()-timedelta(minutes=10),payload={'has_data':True},last_good={'has_data':True})
        self.assertEqual(display_status(self.site,obj)['status'],'stale')
    def test_malformed_private_configuration_does_not_disclose_contents(self):
        self.config.write_text('do-not-disclose')
        response=self.client.get('/api/monitor/?refresh=1')
        self.assertTrue(all(t['status']=='configuration_error' for t in response.data['towers']))
        self.assertNotIn('do-not-disclose',json.dumps(response.data,default=str))
