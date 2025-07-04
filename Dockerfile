# Dockerfile

# --- AŞAMA 1: BUILDER (Derleyici Ortamı) ---
# Bu aşamada, projenin bağımlılıklarını kurmak için gerekli tüm araçlar bulunur.
# Sonuç imajına sadece kurulan paketler taşınır, bu sayede imaj boyutu küçük kalır.
FROM python:3.11-slim AS builder

# Poetry'nin en son sürümünü kur
ENV POETRY_VERSION=1.8.2
RUN pip install "poetry==${POETRY_VERSION}"

# Çalışma dizinini ayarla
WORKDIR /app

# Poetry'nin sanal ortam yaratmasını engelle, paketleri doğrudan sisteme kur.
# Bu, Docker konteynerleri için standart bir yaklaşımdır.
RUN poetry config virtualenvs.create false

# Sadece bağımlılık dosyalarını kopyala. Bu, Docker'ın katman önbelleklemesini (layer caching)
# verimli kullanmasını sağlar. Kod değişse bile bağımlılıklar değişmediyse bu adımlar tekrar çalışmaz.
COPY poetry.lock pyproject.toml ./

# Sadece production bağımlılıklarını kur. --no-dev, pytest gibi geliştirme araçlarını atlar.
RUN poetry install --no-interaction --no-ansi --no-dev

# --- AŞAMA 2: RUNTIME (Çalışma Ortamı) ---
# Bu aşama, uygulamanın çalışacağı son ve hafif imajı oluşturur.
FROM python:3.11-slim AS runtime

# Güvenlik için 'root' olmayan bir kullanıcı oluştur ve kullan
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Çalışma dizinini ayarla
WORKDIR /app

# Derleyici ortamından (builder) sadece kurulan bağımlılıkları kopyala
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Uygulama kodunu kopyala ve oluşturulan kullanıcıya ait olmasını sağla
COPY --chown=appuser:appgroup ./app ./app

# Uygulamanın çalışacağı portu dışarıya aç
EXPOSE 8000

# Konteyner çalıştığında uygulamayı başlatan komut.
# --host 0.0.0.0, uygulamanın konteyner dışından erişilebilir olmasını sağlar.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]