FROM python:3.11-slim-bookworm

LABEL description="AI 书僮 - AI辅助阅读网站"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py shelf.py reader.py book_parser.py prompt.py notes.py reading_log.py ./

RUN mkdir -p shelf

EXPOSE 8501
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=2000

CMD ["streamlit", "run", "app.py"]
