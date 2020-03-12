FROM python:3.7

ENV DEBIAN_FRONTEND="noninteractive"

RUN useradd -ms /bin/bash pi -u 1000

RUN mkdir /etc/privacyidea && chown -R pi /etc/privacyidea

WORKDIR /home/pi

COPY --chown=pi:pi requirements.txt requirements.txt

RUN pip -q install -r requirements.txt && rm -rf ~/.cache/pip

COPY --chown=pi:pi . .

ENV PATH=$PATH:/home/pi/.local/bin

EXPOSE 5000

USER pi