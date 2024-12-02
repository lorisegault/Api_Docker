FROM python:3.11-alpine
RUN apk update
WORKDIR /app
COPY . /app
VOLUME /app/data
EXPOSE 5008
RUN pip install -r requirements.txt
RUN pip install python-multipart
CMD ["python3", "auth.py"]
