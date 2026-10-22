FROM ubuntu:24.04@sha256:a2d43bffc46670d7108bb3c0468c67c5557c4c92e83e1e34cbff1322ad1b94dc
ENV DEBIAN_FRONTEND=noninteractive SOURCE_DATE_EPOCH=1792627200 LC_ALL=C TZ=UTC
COPY infra/pdf-runtime/ubuntu.sources /opt/bootstrap/ubuntu.sources
COPY infra/pdf-runtime/apt-SHA256SUMS /opt/bootstrap/apt-SHA256SUMS
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    cp /opt/bootstrap/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update && \
    cd /var/lib/apt/lists && sha256sum -c /opt/bootstrap/apt-SHA256SUMS && \
    apt-get install -y --no-install-recommends build-essential cmake pkg-config \
    python3 python3-venv ca-certificates libfontconfig1-dev libfreetype6-dev \
    libjpeg-dev libpng-dev libopenjp2-7-dev liblcms2-dev libtiff-dev zlib1g-dev \
    fonts-dejavu-core poppler-data
COPY infra/pdf-runtime/toolchain.json /opt/bootstrap/toolchain.json
COPY scripts/build_crcl_pdf_runtime.py /opt/bootstrap/build.py
RUN python3 /opt/bootstrap/build.py
RUN mkdir -p /opt/equity/equity_ingest /opt/equity/equity_schema /opt/equity/scripts /out /input && \
    touch /opt/equity/equity_ingest/__init__.py /opt/equity/equity_schema/__init__.py /opt/equity/scripts/__init__.py && \
    chmod 1777 /out
COPY packages/ingest/pdf_review.py packages/ingest/pdf_review_worker.py packages/ingest/pdf_exec_worker.py packages/ingest/pdf_transfer.py /opt/equity/equity_ingest/
COPY packages/schema/crcl_history.py /opt/equity/equity_schema/
COPY scripts/crcl_pdf_runtime.py scripts/run_crcl_pdf_proof.py /opt/equity/scripts/
ENV PYTHONPATH=/opt/equity
WORKDIR /opt/equity
USER 65534:65534
