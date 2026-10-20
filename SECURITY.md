# Security and deployment review

Reviewed 20 October 2026. This is an application/code and local-test review,
not a penetration test of the destination VM. The app has not been deployed or
exposed publicly by this review. Public pages can be requested by bots; the goal
is to protect private records and limit abuse, not to promise that bots cannot
connect.

## Changes made

| Area | Previous gap | Protection added |
|---|---|---|
| Password guessing | No login-attempt throttling | Django Axes persists failed attempts in the shared database; five failures for a username/client address pause sign-in for 15 minutes, across team and admin login |
| Proxy spoofing | No verified client-address policy for login protection | X-Real-IP is used only in proxy mode and from an explicitly trusted peer; nginx overwrites forwarded headers |
| Request floods | nginx had no rate or connection limits | Separate authentication, general, static and public-report budgets; a global report-render budget; small authentication request bodies and bounded connections |
| Browser isolation | Private HTML had no Content Security Policy | Same-origin scripts/requests/workers; no plugins/objects; restricted framing and forms; device permissions disabled |
| Private responses | Some authenticated JSON/pages/exports lacked explicit cache instructions | Private/no-store headers cover the workspace, APIs, downloads and exports; intentional prepared-device storage is unchanged |
| Account/session exposure | New passwords could be eight characters; sessions lasted 14 days | Twelve-character minimum for new/changed passwords and 12-hour sessions; existing passwords/accounts are preserved |
| Container contents | Alternate environment files, SQLite sidecars and logs could enter a build | Explicit exclusions for environment variants, DB sidecars, logs and private-key material |
| Logs | Default access logging can record password-reset URLs | nginx's access format omits query strings/Referer and redacts reset-token paths; the container avoids a duplicate unredacted Gunicorn access log |
| Supply chain | No automated vulnerability scan in CI | Pinned login-protection dependency plus a pip-audit check of application requirements |
| Field queue | Temporary proxy throttling could stop a queue as a conflict | HTTP 429 keeps records queued for retry; it does not discard records or require conflict resolution |

Lockouts return HTTP 429 and Retry-After. Requests made during a pause do not
extend it indefinitely. A successful sign-in resets earlier failures for that
client/account. Another account at the same address is not locked by those
failures. nginx separately limits account rotation from one address. These
controls reduce guessing; they do not replace strong passwords or MFA.

## Verification results

- 167 backend tests passed, including 21 security regression checks for lockouts,
  spoofed headers, independent clients, cooldowns, password masking, CSRF,
  redirects, host validation, private routes, CORS and public read-only behavior.
- pip-audit found no known vulnerabilities in the 16 resolved application
  dependency packages at review time, including Django Axes 8.3.1. This is a
  point-in-time advisory check, not a guarantee against undisclosed issues.
- Bundled PDF.js is 6.4.299; the GitHub advisory API reported no reviewed
  advisories affecting that exact version. Dynamic code evaluation is disabled.
- Bandit findings were reviewed. Its medium SQL warning is the BADM display
  string 'select a value from', which is never executed as SQL. Low password
  warnings refer to test fixtures and a backup-command option, not credentials.
- The tracked-text credential scan found development placeholders, documentation
  examples and test values. The retired data-download protocol has never been
  tracked in this repository. Private environment files and real tower endpoints
  remain outside Git and images.
- Browser checks exercised normal login, the workspace, protected PDF rendering,
  and the lockout page under the new browser policy. Security tests and browser
  fixtures use separate databases/accounts; live users are not deliberately
  locked out.

Django's production checks pass without security errors under simulated HTTPS
settings. They retain the intentional W021 warning because HSTS preload is off.
Do not enable preload solely to hide this warning: it needs a separate domain
ownership and permanent-HTTPS decision. Local development still uses DEBUG=True
and HTTP; its production-security warnings are expected locally.

## Required before exposing the VM

1. Use production settings and a new random SECRET_KEY. Set DEBUG=False,
   explicit ALLOWED_HOSTS and the actual HTTPS CSRF origin. Start from
   `deploy/production.env.example`, not a development environment. Its placeholder
   secret must be replaced. Never publish the filled environment file.
2. Install requirements and apply migrations before restarting. Run
   `python manage.py check --deploy` against the real environment. Do not run the
   development server on the internet. Use a supported production server behind
   the HTTPS reverse proxy.
3. Install a valid TLS certificate and adapt `deploy/nginx.conf.example` for the
   actual domain. Run `nginx -t` on the VM before reloading nginx. nginx is not
   installed in the Windows review environment, so that syntax/certificate test
   remains a VM task. The template requires nginx 1.19.4 or newer.
4. Expose only HTTPS and the HTTP-to-HTTPS redirect. Keep the application port,
   PostgreSQL, analyzer ports and media storage private. Allow SSH only through
   the VPN or a restricted administrator address, using keys. Verify firewall
   rules from outside the VM and preserve administrator access before changing
   them.
5. Protect administration, preferably the entire team workspace, with the
   university VPN or an identity proxy with MFA. The app currently uses
   passwords; native MFA is not included. Distributed guessing, credential
   theft and volumetric DDoS need upstream protection as well.
6. Set TRUST_PROXY_HEADERS only when direct access to the backend is blocked.
   Configure TRUSTED_PROXY_NETWORKS with the real proxy peer(s). For Docker this
   may be a specific bridge gateway instead of loopback. If a CDN is used,
   configure nginx real_ip for only its verified address ranges; do not trust
   arbitrary incoming forwarding headers.
7. Keep the private monitor file outside the checkout/web root and readable only
   by the service account. Restrict outbound connectivity to required tower
   hosts/ports where practical. The app sends exact allowlisted TCP read queries,
   does not use LI-COR web/SSH passwords, and never exposes a general socket or
   command proxy. Default device passwords still need protection on the device
   network; the app does not secure exposed analyzer management interfaces.
8. Configure real SMTP for password reset and test delivery. Never use the console
   email backend in production because it prints reset links to logs. Production
   defaults to SMTP, but a copied local .env can explicitly override this.
9. Use a dedicated unprivileged service account. Restrict database/media/backups,
   enable encrypted off-server backups, test restore, and patch the OS, Python,
   dependencies and container images. Review proxy/login warnings and alerts.
10. Treat uploads as untrusted. Files are permission checked and served with safe
    content types, downloads and sandbox headers, but there is no antivirus
    scanner. Add malware scanning if broader upload access is granted. Use only
    trusted field devices: prepared offline copies cannot be revoked remotely.

The public scope deliberately includes sites, visits/observations and caveats,
plus supplied reference figures and eligible scientific INIs. Do not place
passwords, private endpoints or personal/private notes in those public fields.
Public reports do not expose inventory, BADM, internal uploads, the technical
library, calibration logs, account data or tower connection settings.

## Operator recovery and monitoring

An administrator with server access can clear a mistaken lockout using:

```bash
python manage.py axes_reset_username USERNAME
```

This command is for deliberate recovery, not a recurring job. Database-backed
attempts survive process restarts. Review the Axes access-attempt records in
Django administration and restrict access to login/proxy logs. Establish a
retention policy for IP addresses and usernames; remove expired attempt records
through approved maintenance without clearing active lockouts. Rotate nginx
logs and watch disk usage, request rates, HTTP 429s and failed logins.

Session expiry does not delete pending offline records. Sign in again with the
same account to synchronize them; do not clear a device while it has unsynced
records. Tune proxy limits using real traffic, including shared campus/VPN IPs
and offline preparation. Static assets have a separate burst budget so the
service-worker pre-cache can complete.

## Repeating the review

```bash
python manage.py check --deploy
python manage.py test hub
python -m pip install pip-audit==2.10.1
python -m pip_audit -r requirements.txt
```

Audit tools need access to the package/advisory services. Review their findings
rather than automatically upgrading dependencies in production. Never test
password guessing against real user accounts or scan tower/third-party networks
without separate authorization. Report security issues privately to the
repository owner; do not publish passwords, endpoints or exploit details in a
public issue.

Primary references:

- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django authentication scope](https://docs.djangoproject.com/en/5.2/topics/auth/)
- [Django Axes installation and configuration](https://django-axes.readthedocs.io/en/stable/)
- [nginx request limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
