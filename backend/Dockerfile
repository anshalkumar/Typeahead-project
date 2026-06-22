FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy source and dataset into container
COPY . /app/backend
COPY dataset /app/dataset

# Ensure the database path resolves correctly inside the container
ENV TYPEAHEAD_DATASET_PATH=/app/dataset/query_counts.csv

EXPOSE 18080

CMD ["python", "-m", "backend.main"]
