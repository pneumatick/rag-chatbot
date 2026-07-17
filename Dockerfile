FROM python:latest

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh
CMD ["/workspace/entrypoint.sh"]

ENV PORT=5000
EXPOSE 5000