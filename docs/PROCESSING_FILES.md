# Current TraceAnalysis INI files

The maintained source is the
[Carbonique software and settings repository](https://github.com/CARBONI-QUE/UQAM_Software_and_Settings/tree/main/Database/Calculation_Procedures/TraceAnalysis_ini).
Open **Data & processing → TraceAnalysis INI files → Open INI files on GitHub**
to view files, inspect commit history and download the current versions.
The public report links to the same folder.

The app no longer presents a current INI upload/download library. It does not
fetch GitHub files automatically, need a GitHub token, or execute INI contents.
An internet connection and any repository access required by GitHub are needed.

Scientific configuration history and caveat-linked evidence remain in the app.
Those records describe historical settings and affected periods; they are not
assertions that an archived file is the latest configuration. The original
supplied source snapshots remain for provenance. Initial setup no longer seeds
the former working INI library. Existing private revision records and protected
legacy recovery endpoints are retained for backward compatibility and backups.
They are not embedded in the public report. The original W drive files are
never modified.

For developers, `static/hub/processing-files.js` renders the workspace link and
`templates/public_report.html` renders the public link. The fixed upstream URL
in the public projection and module must stay consistent. The original
`ProcessingFile` models and import helper support earlier backups; do not use
them as a second maintained source or run their import during normal updates.
