FROM python:latest
WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY package.json .
RUN apt update && apt install -y nodejs npm

COPY . .
RUN chmod +x entrypoint.sh
CMD ["/workspace/entrypoint.sh"]

ENV PORT=5173
EXPOSE 5000 5173