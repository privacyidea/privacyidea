FROM python:2.7-slim-jessie
LABEL author="Mostafa Hussein <mostafa.hussein91@gmail.com>"
COPY . /home/privacyidea
WORKDIR /home/privacyidea
RUN apt-get update && apt-get install -y --no-install-recommends libc6-dev=2.19-18+deb8u10 gcc=4:4.9.2-2 git=1:2.1.4-2.1+deb8u6 && rm /var/lib/apt/lists/* -R && pip install -r requirements.txt
RUN git submodule init && git submodule update
ARG ADMIN
ENV ADMIN $ADMIN
ARG PASSWORD
ENV PASSWORD $PASSWORD
RUN ./pi-manage createdb && ./pi-manage create_enckey && ./pi-manage create_audit_keys && ./pi-manage admin add $ADMIN -p $PASSWORD
RUN adduser privacyidea --disabled-password --disabled-login --gecos "" --no-create-home --home /home/privacyidea && chown privacyidea:privacyidea /home/privacyidea -R
EXPOSE 5000
USER privacyidea
ENTRYPOINT ["./pi-manage"]
CMD [ "runserver", "-h", "0.0.0.0"]
