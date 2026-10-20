FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home carbonique
COPY . .
RUN DEBUG=True python manage.py collectstatic --noinput && mkdir -p /app/media && chown -R carbonique:carbonique /app
USER carbonique
EXPOSE 8000
CMD ["gunicorn", "carbonique.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
