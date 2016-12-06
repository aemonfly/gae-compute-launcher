FROM debian:jessie-slim
MAINTAINER "Frank A. J. Wilson"
RUN apt-get -y update && apt-get -y install python curl unzip
RUN curl -s https://storage.googleapis.com/pub/gsutil.zip \
    -o /tmp/gsutil.zip && unzip /tmp/gsutil.zip && rm /tmp/gsutil.zip
ADD datetimeupload.sh /
ENTRYPOINT ["/bin/bash", "/datetimeupload.sh"]
