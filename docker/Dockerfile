# Erik Petrosyan ©
FROM python:3.11-slim AS main

LABEL version="1.0"
LABEL author="ERIK_PETROSYAN"
LABEL description="CS2 teammate finder bot"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos "" erik && chown -R erik /app
USER erik

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=erik:erik . .

CMD ["python", "player_finder.py"]

EXPOSE 2222
