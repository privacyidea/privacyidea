FROM python:3.7

ENV DEBIAN_FRONTEND="noninteractive"
ENV PATH=$PATH:/home/pi/privacyidea/.local/bin:/home/pi/.local/bin

RUN useradd -ms /bin/bash pi -u 1000

RUN mkdir /etc/privacyidea /home/pi/privacyidea && chown -R pi /etc/privacyidea /home/pi/privacyidea

USER pi

WORKDIR /home/pi/privacyidea

COPY requirements.txt requirements.txt

RUN pip -q install -r requirements.txt && rm -rf ~/.cache/pip

COPY . .

EXPOSE 5000