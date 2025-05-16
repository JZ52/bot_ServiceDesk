FROM python:3.11-slim


WORKDIR /app
COPY . /app
RUN if [ ! -f /app/processed_isd.json ]; then echo '{}' > /app/processed_isd.json; fi
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT [ "python", "bot_SD.py" ]
