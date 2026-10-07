FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# `apt-get upgrade` shart: python:3.11-slim (Debian 13) o'z paketlarida hali
# tuzatilgan versiyasi chiqqan HIGH/CRITICAL CVE'lar bor (gzip, libpcre2-8-0,
# libsqlite3-0, perl-base) va Trivy `--ignore-unfixed` bilan shu yerdan oladi.
# CI `--build-arg OS_REFRESH=$CI_PIPELINE_ID` beradi; qiymat o'zgarganda shu va
# keyingi qatlamlar kache'dan chiqadi.
ARG OS_REFRESH=0
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd \
    --create-home \
    --uid 1001 \
    --shell /usr/sbin/nologin \
    appuser

# Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Trivy HIGH (python-pkg): setuptools ichidagi vendored jaraco.context va
# ensurepip'dagi wheel .whl — ish vaqtida kerak emas, obrazdan olib tashlanadi.
RUN pip uninstall -y setuptools wheel \
    && rm -rf /usr/local/lib/python3.11/ensurepip

# Application fayllari
COPY --chown=appuser:appuser main.py /app/main.py
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser config/ /app/config/

# main.py start'da logging_config/sentry ni import qiladi va alembic.ini +
# migrations/ bilan migratsiyani suradi — bularsiz konteyner crash bo'ladi.
COPY --chown=appuser:appuser logging_config.py sentry.py /app/
COPY --chown=appuser:appuser migrations/ /app/migrations/

# Sozlamalar muhit o'zgaruvchilaridan keladi (Railway — Variables); lokal
# .env (API kalitlari bilan) obrazga ATAYLAB kiritilmaydi (.dockerignore).
COPY --chown=appuser:appuser alembic.ini /app/

# PROFILE
ARG PROFILE=prod
ENV PROFILE=${PROFILE}

# Versiya kuzatuvi: `/api/health` shu qiymatni qaytaradi.
ARG GIT_COMMIT=dev
ENV GIT_COMMIT=${GIT_COMMIT}

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# `/actuator/health` token talab qilmaydi va DB'ga urilmaydi.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/actuator/health" || exit 1

CMD ["python", "main.py"]