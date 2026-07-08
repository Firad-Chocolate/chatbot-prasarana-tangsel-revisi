FROM rasa/rasa:3.6.21-full

WORKDIR /app
COPY . .

USER root
# Catatan: TIDAK reinstall paket "rasa"/"rasa-sdk" -- base image ini sudah
# menyertakan versi yang cocok dengan model hasil training. Reinstall bisa
# menyebabkan mismatch versi dan model gagal dimuat.
RUN pip install --no-cache-dir psycopg2-binary python-dotenv

USER 1001
EXPOSE 5005

CMD ["run", "--enable-api", "--cors", "*", "--credentials", "credentials.yml", "--endpoints", "endpoints.yml"]

