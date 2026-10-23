FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && groupadd --gid 10001 kubedoctor \
    && useradd --uid 10001 --gid kubedoctor --no-create-home kubedoctor

USER 10001:10001
ENTRYPOINT ["kubedoctor"]
CMD ["--help"]

