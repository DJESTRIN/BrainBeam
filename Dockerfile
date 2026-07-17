FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/brainbeam

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        pkg-config \
        libblosc-dev \
        libblosc1 \
        libgl1 \
        libglib2.0-0 \
        libhdf5-dev \
        libjpeg62-turbo \
        libjpeg62-turbo-dev \
        liblz4-1 \
        liblz4-dev \
        libopenjp2-7 \
        libopenjp2-7-dev \
        libsnappy-dev \
        libsnappy1v5 \
        libtiff-dev \
        libtiff6 \
        libxml2 \
        libxml2-dev \
        libxslt1-dev \
        libxslt1.1 \
        libzstd-dev \
        libzstd1 \
        tk \
        zlib1g \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN python -c "from pathlib import Path; p=Path('requirements.txt'); data=p.read_bytes(); text=data.decode('utf-16le') if b'\x00' in data[:256] else data.decode('utf-8-sig'); lines=[line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]; Path('requirements.docker.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')" \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.docker.txt \
    && python -m pip install customtkinter \
    && python -m pip install --no-deps . \
    && rm -f requirements.docker.txt

RUN useradd --create-home --shell /bin/bash brainbeam \
    && chown -R brainbeam:brainbeam /opt/brainbeam

USER brainbeam

CMD ["/bin/bash"]
