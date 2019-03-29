.. _job_queue:

Job Queue
=========

.. index:: job queue, task queue, queue

privacyIDEA workflows often entail some time-consuming tasks, such as sending mails or SMS or saving usage statistics. Executing such tasks during the handling of API requests negatively affects performance. Starting with version 3.0, privacyIDEA allows to delegate certain tasks to external worker processes by using a job queue.

As an example, assume that privacyIDEA receives an authentication request by a user with an email token (see :ref:`email_token`) via HTTP. privacyIDEA will send a one-time password via E-Mail. In order to do so, it communicates with a SMTP server. Normally, privacyIDEA handles all communication during the processing of the original authentication request, which increases the response time for the HTTP request, especially if the SMTP server is at a remote location.

A job queue can help to reduce the response time as follows. Instead of communicating with the SMTP server during request handling, privacyIDEA stores a so-called *job* in a job queue which says "Send an E-Mail to xyz@example.com with content '...'". privacyIDEA does not wait for the E-Mail to be actually sent, but already sends an HTTP response. An external *worker process* then retrieves the job from the queue and actually sends the corresponding E-Mail.

Using a job queue may improve the performance of your privacyIDEA server in case of a flaky connection to the SMTP server. Authentication requests that send E-Mails are then handled faster (because the privacyIDEA server does not actually communicate with the SMTP server), which means that the corresponding web server worker thread can handle the next request faster.

privacyIDEA 3.0 implements a job queue based on `huey`_ which uses a `Redis`_ server to store jobs. As of version 3.0, privacyIDEA allows to offload sending mails to the queue. Other jobs will be implemented in future versions.

Configuration
-------------

The job queue is disabled by default. In order to enable it, add the following configuration option to ``pi.cfg``::

	PI_JOB_QUEUE_CLASS = 'privacyidea.lib.queues.huey_queue.HueyQueue'

After a server restart, you will be able to instruct individual SMTP servers to send all mails via the job queue by checking a corresponding box in the SMTP server configuration (see :ref:`smtpserver`). This means that you can have separate SMTP server configurations, some of which send mails via the job queue, some of which send mails during the request processing.

Note that you need to run a `Redis`_ server which is reachable for the privacyIDEA server. By default, huey assumes a locally running Redis server. You can use a configuration option to provide a different URL (`see here <https://redis-py.readthedocs.io/en/latest/#redis.ConnectionPool.from_url>`_ for information on the URL format)::

	PI_JOB_QUEUE_URL = 'redis://somehost'

In addition to the privacyIDEA server, you will have to run a worker process which fetches jobs from the queue and executes them. You can start it as follows::

	privacyidea-queue-huey

By default, the worker process logs to ``privacyidea-queue.log`` in the current working directory. You can pass a different logfile by using the ``-l`` option::

	privacyidea-queue-huey -l /var/log/queue.log

As the script is heavily based on the huey consumer script, you can find information about additional options in the `huey documentation <https://huey.readthedocs.io/en/latest/consumer.html#options-for-the-consumer>`_.

Note that a side-effect of the queue is that the privacyIDEA server will not throw or log errors if a mail could not be sent. Hence, it is important to monitor the queue log file for errors.

.. _Redis: https://redis.io/
.. _huey: https://huey.readthedocs.io/en/latest/
