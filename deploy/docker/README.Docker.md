privacyIDEA and Docker
======================

We provide a Dockerfile to create a simple privacyIDEA docker container which
currently only contains the runnable code with the gunicorn WSGI server.

> **_NOTE:_**  This is currently very much work-in-progress so expect breaking changes!

Build the container image with:
```
docker build . -f deploy/docker/Dockerfile -t <pi-tag>
```

Run the container with:
```
docker run -p 8080:80 <pi-tag>:latest
```

A volume is automatically created and mounted at `/etc/privacyidea` in the
container. An existing volume can be given at the container start with:
```
docker run -v <volume-id>:/etc/privacyidea -p 8080:80 <pi-tag>:latest
```

Some configuration data is required at `/etc/privacyidea` for this container to
work. See  https://privacyidea.readthedocs.io/en/latest/installation/pip.html#database
and https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html#cfgfile
for configuration options.

Commands can be run inside the container with:
```
docker exec -i <container name> pi-manage ...
```

For example to import existing policies run:
```
cat <policy template yaml> | docker exec -i <container name> pi-manage config import
```

TODO:
-----

* Don't start the container if the configuration is missing or incomplete
  * Alternatively create a running configuration during container startup
* Pass configuration parameters via variables for better use with `compose`
* Create a default logging configuration for docker to log everything to `stdout`
