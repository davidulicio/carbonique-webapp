"""Start a disposable local server for automated browser tests only."""
import hashlib,os,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
import dotenv
dotenv.load_dotenv=lambda *args,**kwargs:None

def pdf(label):
    stream=f'BT /F1 12 Tf 72 720 Td ({label}) Tj ET'.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=b'%PDF-1.4\n';offsets=[0]
    for i,value in enumerate(objects,1):offsets.append(len(data));data+=f'{i} 0 obj\n'.encode()+value+b'\nendobj\n'
    xref=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return data

with tempfile.TemporaryDirectory(prefix='carbonique-browser-') as folder:
    os.environ.update(BROWSER_TEST_ROOT=folder,DJANGO_SETTINGS_MODULE='tests.browser.settings',DEBUG='True',DATABASE_URL='',SECRET_KEY='isolated-browser-fixture-only-not-a-deployment-secret')
    import django
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from django.core.files.base import ContentFile
    from inventory.models import Site
    from hub.models import TeamMember,Protocol
    call_command('migrate',verbosity=0)
    for code in ['TEST_A','TEST_B']:Site.objects.create(code=code,name='Browser tower '+code,date_activated='2025-01-01')
    for name in ['browser-a','browser-b']:
        user=get_user_model().objects.create_user(name,password='Disposable-browser-password-2026',first_name=name)
        TeamMember.objects.create(user=user,role='admin')
    data=pdf('Protocol revision one')
    guide=Protocol(title='Browser maintenance guide',category='maintenance',revision='Revision one',filename='guide.pdf',size=len(data),sha256=hashlib.sha256(data).hexdigest())
    guide.file.save('guide.pdf',ContentFile(data),save=True)
    call_command('runserver','127.0.0.1:8786',use_reloader=False,verbosity=0)
