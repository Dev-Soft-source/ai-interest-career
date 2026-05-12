# Use Python 3.13 slim base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY backend /app/backend

# Set Python path
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
