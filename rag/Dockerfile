# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app
# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=600 --retries=10 torch==2.14.1+cpu --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --default-timeout=600 --retries=10 -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the FastAPI application using Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]