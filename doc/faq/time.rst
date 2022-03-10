.. _faq_time:

Time is sensitive in privacyIDEA
--------------------------------

.. index:: Time, Time server, NTP

The time of your system is used at many different scenarios. It is crucial that your
privacyIDEA system has a correct, well defined time.

Tokens
~~~~~~

TOTP tokens are operating based on the unix system time. If the time of your system is not set correctly, TOTP tokens
might not work at all.
If the time of your system is drifting, TOTP tokens, that once worked could stop working if the time drift gets
to big to quick.

Push tokens use the time during enrollment, for synchronization and for the poll functionality.
To avoid replay attacks the Push tokens send a timestamp during the poll request. If you system is off only by a few
minutes, the poll mechanism of Push tokens will not work.

System and Logs
~~~~~~~~~~~~~~~

If you have a redundant setup, you need to ensure, that both systems have the same - preferably the correct - time.
Otherwise you will get an unsorted audit log.

For a useful audit log and for a useful log file you should ensure that your system has the correct time.
Otherwise you will not be able to correlate events with other systems.

Set up NTP
~~~~~~~~~~

On a Linux system running `systemd` you can use the `timesyncd`.

If your privacyIDEA system is running in a Windows domain, each domain controller also acts as a NTP server.
In the file `/etc/systemd/timesyncd.conf` you can configure your local NTP servers like::

    [Time]
    NTP=dc01.your.domain dc02.your.domain dc03.your.domain

You can restart the service::

    systemctl restart systemd-timesyncd

and check the status with::

    timedatectl status
    systemctl status systemd-timesyncd

