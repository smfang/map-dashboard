FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8051

CMD ["gunicorn", "map_dashboard:server", "--bind", "0.0.0.0:8051"] 