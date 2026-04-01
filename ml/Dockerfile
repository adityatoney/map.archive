FROM python:3.11-slim

WORKDIR /app

COPY serve/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY serve/ .

EXPOSE 8001

CMD ["uvicorn", "handler:app", "--host", "0.0.0.0", "--port", "8001"]
