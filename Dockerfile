FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY m6_dashboard/ ./m6_dashboard/

EXPOSE 8501

CMD ["streamlit", "run", "m6_dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
