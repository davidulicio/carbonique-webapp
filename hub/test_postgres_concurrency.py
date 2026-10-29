"""These tests exercise real PostgreSQL row locks, not SQLite approximations."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from inventory.models import Site, Equipment
from .models import TeamMember,Task,TaskActivity,OperationReceipt,Deployment
from .services import apply_operation,Conflict


@skipUnless(connection.vendor=='postgresql','PostgreSQL row-lock verification runs in the PostgreSQL CI job.')
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.site=Site.objects.create(code='LOCKS',name='Lock test',date_activated='2025-01-01')
        self.user=get_user_model().objects.create_user('lock-user');TeamMember.objects.create(user=self.user,role='manager')
        self.other=get_user_model().objects.create_user('other-lock-user');TeamMember.objects.create(user=self.other,role='manager')
        self.task=Task.objects.create(site=self.site,title='Concurrent work')
    def operation(self,kind,payload):
        return dict(id=str(uuid.uuid4()),entity_id=str(self.task.pk),kind=kind,site_id=self.site.pk,payload=payload,occurred_at=timezone.now().isoformat(),base_version=1)
    def concurrent(self,functions):
        barrier=Barrier(len(functions))
        def run(function):
            close_old_connections()
            try:barrier.wait(timeout=10);return function()
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=len(functions)) as pool:
            futures=[pool.submit(run,function) for function in functions]
            return [future.result(timeout=30) for future in futures]
    def test_duplicate_receipts_and_activities_are_serialized(self):
        operation=self.operation('task.comment',{'text':'Checked once'})
        def run():return apply_operation(get_user_model().objects.get(pk=self.user.pk),operation)
        results=self.concurrent([run,run]);self.assertEqual(results[0],results[1])
        self.assertEqual(OperationReceipt.objects.count(),1);self.assertEqual(TaskActivity.objects.count(),1)
    def test_two_edits_cannot_both_accept_the_same_version(self):
        def edit(title):
            def run():
                try:apply_operation(get_user_model().objects.get(pk=self.user.pk),self.operation('task.edit',{'title':title}));return 'saved'
                except Conflict:return 'conflict'
            return run
        self.assertCountEqual(self.concurrent([edit('First'),edit('Second')]),['saved','conflict'])
        self.task.refresh_from_db();self.assertEqual(self.task.version,2)
    def test_overlapping_deployments_lock_the_equipment(self):
        gear=Equipment.objects.create(instrument='One sensor',date_purchased='2025-01-01')
        def deploy(user_id):
            def run():
                client=APIClient();client.force_authenticate(get_user_model().objects.get(pk=user_id))
                return client.post('/api/deployments/',{'site':self.site.pk,'equipment':gear.pk,'installed_at':(timezone.now()-timedelta(minutes=1)).isoformat()},format='json').status_code
            return run
        self.assertCountEqual(self.concurrent([deploy(self.user.pk),deploy(self.other.pk)]),[201,400]);self.assertEqual(Deployment.objects.count(),1)
