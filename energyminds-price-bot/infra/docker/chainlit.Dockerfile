FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.chainlit.txt ./requirements.chainlit.txt
RUN pip install --no-cache-dir -r requirements.chainlit.txt

COPY . .

EXPOSE 8001
CMD ["chainlit", "run", "app/chatbot/app.py", "-h", "0.0.0.0", "-p", "8001"]
