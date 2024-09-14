FROM python:3.11
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg
CMD ["bash", "cloud.sh"]
