FROM python:3.11

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "main.py" ]

ENV PORT=5000
EXPOSE 5000