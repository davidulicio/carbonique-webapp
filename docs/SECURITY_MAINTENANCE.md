# Security maintenance, 26 October 2026

This review covers the application source, pinned Python libraries, bundled PDF
viewer, CI workflow and deployment examples. It is not a scan of the Arbutus VM
or evidence that its running packages have been patched. Follow this supplement
alongside the [Arbutus installation guide](ARBUTUS_INSTALLATION.md).

## GitHub failure and application changes

The [21 October run](https://github.com/davidulicio/carbonique-webapp/actions/runs/39624832001)
failed at **Audit application dependencies**. Installation and browser syntax
checks succeeded; later Django checks and tests were skipped. The notification
also reported deprecated action runtimes and a forthcoming `ubuntu-latest`
image change. The audit remains a required check; no advisories are ignored.

A fresh audit of the previous requirements on 26 October reported 40 findings
across REST framework and Pillow. This current count may include advisories
published after the original failed run; the email does not contain its detailed
package log. These are dependency advisories, not 40 confirmed exploitable paths
in this application.

| Component | Assessment and action |
| --- | --- |
| Django REST framework | Updated 3.17.2 to **3.18.3**. Covers excessive Accept-header parsing (CVE-2026-114138), attacker-selected JSON compression codecs (CVE-2026-114136), and token deletion (CVE-2026-114137). The app uses session authentication, so the token revocation feature is not enabled. |
| Pillow | Updated 12.3.0 to **13.0.0**, which fixes the image-decoder issues listed in its security release. File extensions alone previously did not limit Pillow's decoder selection. Upload validation now selects only the matching JPEG, PNG, GIF or WebP decoder and rejects decompression-bomb warnings as validation errors. |
| Django | Retained **5.2.18**, the patched LTS release for the 6 October advisories. No framework major-version migration is needed for those fixes. |
| PDF.js | Retained **6.4.299**, the latest upstream release at review. Reviewed the maintainer advisory list; it already includes the published fixes. Dynamic code evaluation remains disabled. |
| Gunicorn | Retained **23.0.0**. No applicable reviewed advisory was returned for this version by the dependency audit. Keep it behind the configured proxy; do not enable optional parsers, control interfaces or permissive forwarding as a workaround. |
| CI | Updated official actions to verified full commit hashes with Node 24 runtimes, disabled checkout credential persistence, selected Ubuntu 24.04 explicitly, and set Python **3.12.16** / Node **24.22.1**. All local browser modules are syntax checked. |
| Installer and image | CI and Docker upgrade pip to **26.2.2**, which bundles the updated certificate set. Docker rejects upstream Python 3.12 below 3.12.16. This does not replace patching Python/OpenSSL or the operating system trust store. |
| Ongoing checks | The workflow runs on pushes, pull requests, manual dispatch and weekly. Dependabot proposes Python, action and Docker dependency updates weekly. Nothing auto-merges or deploys. Exact Python and Node versions in the workflow need deliberate review when new security releases arrive. |
| nginx examples | Disabled TLS session tickets as a precaution while the host is patched. Both proxy examples redact reset URLs in HTTP and HTTPS access logs. |

## Host updates required before public deployment

### Python and certificate trust

Python's [25 October 3.12.16 security release](https://www.python.org/downloads/release/python-31216/)
blocks compromised eMudhra intermediate CA keys (CVE-2026-115557), updates Expat,
and includes additional archive and standard-library fixes. Use **3.12.16 or a
later maintained security release** for upstream Python 3.12 deployments. Other
supported Python branches have corresponding fixes in 3.11.18, 3.13.18,
3.14.10 and 3.15.2. Review library compatibility before changing Python branches.

Ubuntu may backport fixes without changing the upstream `3.12.x` version shown
by `python --version`. For the VM's distribution Python, verify the **installed
Ubuntu package revision and the vendor CVE status**; a completed `apt upgrade`
or an unchanged version string alone does not prove a newly announced fix is
available. Never replace `/usr/bin/python3` or add an unreviewed package source
to force a version update. If a needed vendor patch is pending, delay public
exposure or use a verified patched runtime with a separately recreated virtual
environment, then test the app before switching its systemd service.

The Windows development environment was originally created with Python 3.12.10.
Upgrading the requirements inside that environment does not upgrade its
interpreter. Install a patched supported Python and recreate the environment for
continued use with untrusted files. Keep `.env`, the database and media outside
any environment replacement operation.

### Node.js and PHP

[Node's 21 October security release](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
includes the Brotli decoder RCE (CVE-2026-111497), DNS/TLS validation fixes and
certificate distrust updates. CI now selects **24.22.1**. The app does not run a
Node server or need npm packages in production. Other Node services on the same
VM must be updated independently; changing this workflow does not patch them.

This app has **no PHP runtime or PHP-FPM requirement**. If the existing VM serves
other PHP applications, its administrator must review
[PHP's advisory](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
for CVE-2026-109619 and the
[23 October follow-up](https://www.php.net/archive/2026.php).
PHP recommends `session.upload_progress.enabled=0` until its next regular bugfix
release, including when the initial security release is already installed.
Apply and verify that setting in the actual PHP-FPM/Apache configuration for
those other sites, then restart the relevant workers. No PHP packages are added
to Carbonique.

### nginx and existing services

Review the [upstream nginx advisory list](https://nginx.org/en/security_advisories.html)
and the distribution package's backports. Upstream lists **1.30.6 / 1.31.7** as
fixed for the latest group of issues, including alias/rewrite buffer overflow,
HTTP/3 injection, AIO use-after-free and TLS session-ticket forgery. These are
configuration-dependent. The supplied app proxy uses neither alias/rewrite nor
HTTP/3/AIO; another virtual host or an inherited global configuration may do so.
The TLS ticket issue concerns client-certificate authentication, which this app
does not configure. Disabling tickets in the examples reduces that exposure
where such global settings exist and does not replace updating nginx.

At review, Ubuntu's [alias/rewrite CVE page](https://ubuntu.com/security/CVE-2026-15176)
and [TLS ticket CVE page](https://ubuntu.com/security/CVE-2026-97629) still marked
Ubuntu 24.04 as **Needs evaluation**. Do not claim that the VM is patched based
only on installing its currently offered packages. Check the current notices,
module configuration and any co-hosted applications with the VM administrator.

### Native Ubuntu installation update procedure

Use a planned maintenance window because this VM also collects tower data.
Confirm a restorable database/media/configuration backup and coordinate any
reboot or service restart with the acquisition processes. Run these inspection
commands on the VM as its authorized administrator:

```bash
sudo apt update
apt list --upgradable
apt-cache policy python3.12 libpython3.12-stdlib nginx openssl ca-certificates
python3 --version
sudo nginx -V
sudo systemctl status carbonique --no-pager
```

Review the offered packages and vendor security notices. Apply supported updates
with `sudo apt upgrade` once coordinated. Review any need to reboot rather than
automatically rebooting an acquisition server. Existing running workers retain
old code until restarted.

For the app's dedicated virtual environment, after ensuring its interpreter is
patched or vendor-fixed, use the source checkout owner's account:

```bash
cd /srv/carbonique-webapp
git pull --ff-only
.venv/bin/python -m pip install --upgrade pip==26.2.2
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python manage.py check
sudo -u carbonique .venv/bin/python manage.py migrate --noinput
sudo -u carbonique .venv/bin/python manage.py collectstatic --noinput
sudo -u carbonique .venv/bin/python manage.py check --deploy
sudo nginx -t
sudo systemctl restart carbonique
sudo systemctl reload nginx
sudo systemctl status carbonique --no-pager
```

Stop on the first failure. The existing secret remains in `/etc/carbonique/app.env`;
commands must load the same production settings described in the installation
guide. If recreating the environment, preserve its `carbonique` group read/execute
permissions. Do not run seed imports or create accounts again during this patch
update. This update adds no database migration. Review `security.W021` separately:
HSTS preload is intentionally disabled until the domain owner chooses enrollment.
Check the public report, staff login, an authorized upload and monitor snapshots
after restart. Recheck tower acquisition and other co-hosted services too.

### Docker installations

Rebuild with `docker compose build --pull --no-cache` to pick up base-image and
system-library updates; installing new Python requirements alone is insufficient.
Inspect the actual interpreter in the rebuilt image:

```bash
docker compose run --rm --no-deps web python --version
```

On 26 October the registry did **not** yet provide the `python:3.12.16-slim` tag;
the rolling `python:3.12-slim` tag was last updated on 22 October. Consequently
this repository does not claim that its current rolling base already contains
the 25 October fix. The Dockerfile now **refuses to build with upstream Python
3.12 older than 3.12.16**. Until the rolling tag is patched, this failure is
intentional. Wait for a verified patched image or pass an independently reviewed
Python 3.12.16+ base with `--build-arg PYTHON_IMAGE=YOUR_VERIFIED_BASE`. This Docker
configuration supports the 3.12 series; switching branches needs a separate
compatibility and security review. Check the actual runtime
again even after a successful pull. Retest and recreate the web container after
updating; preserve database/media volumes. Never use `docker compose down -v`
for a normal security update. Update the PostgreSQL image and other services
under the same backup and maintenance procedure.

## Reproducing the checks

Use an isolated virtual environment and the pinned requirements. The audit tool
can be installed in a separate environment to avoid adding tools to production:

```bash
python -m pip install --upgrade pip==26.2.2
python -m pip install -r requirements.txt
python -m pip check
python -m pip install pip-audit==2.10.1
python -m pip_audit -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test hub
```

The audit searches known Python-package advisories. It does not audit the running
CPython interpreter, OS libraries, Docker base, nginx, browser versions or bundled
JavaScript. Those require the separate upstream/vendor checks above. The app's
existing access controls, CSRF, private file delivery, public report isolation,
login lockouts and read-only tower command allowlist remain part of the regression
suite. Uploaded documents are not antivirus-scanned; preserve role restrictions
and keep private files outside the web server's public directories.

## Verification result

All 179 tests passed on Ubuntu 24.04 with Python 3.12.16 and in the updated
Windows app environment. The patched Python requirements returned zero known
advisories on both platforms (15 Linux packages, 16 Windows packages). Static
collection, Django checks, migration drift and browser module syntax passed.
Ten new tests cover request parsing and restricted raster-image validation.
Simulated production checks returned only the intentional HSTS preload warning.
The Docker version check rejects the old local interpreter and accepts the
patched one. The updated workflow has not yet been run by GitHub because this
commit has not been pushed. No live VM or research data was modified.

## Primary references

- [Django REST framework security advisories](https://github.com/encode/django-rest-framework/security/advisories)
- [Pillow 13.0.0 release and security notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
- [Django 5.2.18 security release](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/)
- [Python security release announcement, 26 October](https://blog.python.org/2026/10/python-3152-31410-31318-31216-31118/)
- [Node.js 24.22.1 security release](https://nodejs.org/en/blog/release/v24.22.1)
- [pip certificate bundle update](https://pip.pypa.io/en/stable/news/)
- [nginx security advisories](https://nginx.org/en/security_advisories.html)
- [PDF.js maintainer advisories](https://github.com/mozilla/pdf.js/security/advisories)
- [GitHub Actions security practices](https://docs.github.com/en/actions/reference/security/secure-use)
