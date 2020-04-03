FROM ubuntu:18.04

ENV PRIVACYIDEA_VERSION=v3.2.2
ENV PRIVACYIDEA_CONFIGFILE=/etc/privacyidea/pi.cfg

RUN apt-get update \
  # build deps
  && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libffi-dev \
    libgdbm-dev \
    libjpeg-dev \
    libldap2-dev \
    libncurses5-dev \
    libnss3-dev \
    libpq-dev \
    libreadline-dev \
    libsasl2-dev \
    libssl-dev \
    libxslt1-dev \
    libz-dev \
    zlib1g-dev \
  # python3
  && apt-get install -y \
    python3 \
    python3-pip \
  # apache, mods and wsgi (python support)
  && apt-get install -y \
    apache2 \
    apache2-dev \
    libapache2-mod-wsgi-py3 \
  && rm -f /etc/apache2/sites-enabled/*.conf \
  && a2enmod wsgi auth_digest \
  # install stunnel
  && apt-get install -y stunnel4 \
  # add user
  && adduser --disabled-password --disabled-login --gecos "" privacyidea \
  && mkdir -p /opt/privacyidea \
  ## fix log dir
  && mkdir -p /var/log/privacyidea && touch /var/log/privacyidea/privacyidea.log && chmod a+rw /var/log/privacyidea/privacyidea.log \
  # check python
  && python3 --version \
  # install privacyIDEA
  && pip3 install --no-cache-dir "privacyidea==$PRIVACYIDEA_VERSION" \
  # mysql driver
  && pip3 install --no-cache-dir 'pymysql-sa==1.0' 'PyMySQL==0.9.3' \
  # deps
  && pip3 install --no-cache-dir -r "https://raw.githubusercontent.com/privacyidea/privacyidea/$PRIVACYIDEA_VERSION/requirements.txt" \
  # cleanup
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/privacyidea

COPY apache.conf /etc/apache2/sites-enabled/privacyidea.conf

COPY privacyideaapp.py /opt/privacyidea/privacyideaapp.wsgi

CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
