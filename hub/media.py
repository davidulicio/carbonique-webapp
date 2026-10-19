"""Range-capable file delivery; callers enforce the record's site permissions."""
import re
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header


def stream_file(request, field, filename, content_type, download=False):
    from .views import file_response
    try:
        size = field.size
    except (OSError, ValueError):
        raise Http404("The media file is missing from storage.")
    requested_range = request.headers.get("Range")
    if requested_range and not download:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range)
        if not match or not any(match.groups()):
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end or start >= size:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        def chunks():
            with field.open("rb") as handle:
                handle.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = handle.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        response = StreamingHttpResponse(chunks() if request.method != "HEAD" else (), status=206, content_type=content_type)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Content-Length"] = end-start+1
    elif request.method == "HEAD":
        response = HttpResponse(content_type=content_type)
        response["Content-Length"] = size
    else:
        response = file_response(field, filename, content_type, inline=not download)
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Disposition"] = content_disposition_header(download, filename)
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response
