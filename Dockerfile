ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
# The upstream 3.12 image must include the October certificate distrust fix.
RUN python -c "import sys; assert sys.version_info[:2] == (3, 12) and sys.version_info[:3] >= (3, 12, 16), 'This image requires patched upstream Python 3.12.16 or newer in the 3.12 series. Pull a patched base before deployment.'"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2 && python -m pip install --no-cache-dir -r requirements.txt && useradd --create-home carbonique
COPY . .
RUN DEBUG=True python manage.py collectstatic --noinput && mkdir -p /app/media && chown -R carbonique:carbonique /app
USER carbonique
EXPOSE 8000
CMD ["gunicorn", "carbonique.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
