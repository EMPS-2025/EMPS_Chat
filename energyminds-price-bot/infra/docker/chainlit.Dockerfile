FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app


COPY requirements.chainlit.txt ./requirements.chainlit.txt
RUN pip install --no-cache-dir -r requirements.chainlit.txt

COPY requirements.txt ./

RUN pip install --no-cache-dir chainlit==1.0.200 fastapi==0.108.0 httpx==0.24.1 pydantic==2.6.4

RUN pip install --no-cache-dir chainlit==1.0.200 httpx==0.27.0 pydantic==2.6.4


COPY . .

EXPOSE 8001
CMD ["chainlit", "run", "app/chatbot/app.py", "-h", "0.0.0.0", "-p", "8001"]
