FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py field_guide.py index.html boars.html sighting.html ./
COPY assets ./assets
COPY setup.sh /app/setup.sh

RUN sed -i 's/\r$//' /app/setup.sh \
    && chmod 755 /app/setup.sh

RUN useradd --create-home --uid 10001 hunter
USER hunter

EXPOSE 8080

CMD ["/app/setup.sh"]
