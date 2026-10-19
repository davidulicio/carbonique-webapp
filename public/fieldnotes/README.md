# Public Field Notes

Replace **index.html** in this folder with the complete, self-contained HTML report from `carbonique_fieldnotes`. Keep the filename `index.html`.

The public URL is **/fieldnotes/**. No sign-in is required. The original maintenance timeline, search, caveats, plots, site cards and tower diagrams run inside the public section.

The server reads this file on each request: updating it on the running server (or a mounted folder) needs no database import or process restart. If you update it in GitHub, deploy/pull the new commit to your server; a GitHub commit alone cannot update another machine's filesystem. A newly built Docker image must be redeployed, or this folder can be mounted as a volume.

The report is isolated in a sandbox. Its JavaScript cannot read the private app's cookies or call authenticated APIs. Use embedded CSS, JavaScript, plots and photographs; external scripts and local relative asset files are intentionally blocked. The report from the supplied repository already embeds its assets.

This public HTML is an editorial snapshot. Updating it does not modify database records. To also update the internal database reference, use `scripts/extract_fieldnotes.py` and `import_fieldnotes` as documented in `docs/IMPORTS.md`. Imported records are not silently overwritten on later runs.

Do not add private account information or credentials to the public report. Everything in this file is public.
