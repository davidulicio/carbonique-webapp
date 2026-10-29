"""Isolated browser fixtures never use deployment credentials or storage."""
import os
from pathlib import Path
from carbonique.settings import *
TEST_ROOT=Path(os.environ['BROWSER_TEST_ROOT'])
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':TEST_ROOT/'browser.sqlite3','OPTIONS':{'timeout':30}}}
MEDIA_ROOT=TEST_ROOT/'media'
STATIC_ROOT=TEST_ROOT/'staticfiles'
DEBUG=True
ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
MONITOR_STATIONS_FILE=''
PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'null':{'class':'logging.NullHandler'}},'root':{'handlers':['null']}}
