.. _job_queue:

Job Queue
=========

.. index:: job queue, task queue, queue

privacyIDEA workflows often entail some time-consuming tasks, such as sending emails or SMS or saving usage statistics. Executing such tasks during the handling of API requests negatively affects performance. privacyIDEA can delegate certain tasks to external worker processes by using a job queue.

.. note:: The job queue is removed in privacyIDEA 3.15.

As an example, assume that privacyIDEA receives an authentication request by a user with an email token (see :ref:`email_token`) via HTTP. privacyIDEA will send a one-time password via email. In order to do so, it communicates with an SMTP server. Normally, privacyIDEA handles all communication during the processing of the original authentication request, which increases the response time for the HTTP request, especially if the SMTP server is at a remote location.

A job queue can help to reduce the response time as follows. Instead of communicating with the SMTP server during request handling, privacyIDEA stores a so-called *job* in a job queue which says "Send an email to xyz@example.com with content '...'". privacyIDEA does not wait for the email to be actually sent, but already sends an HTTP response. An external *worker process* then retrieves the job from the queue and actually sends the corresponding email.

Using a job queue may improve the performance of your privacyIDEA server in case of a flaky connection to the SMTP server. Authentication requests that send emails are then handled faster (because the privacyIDEA server does not actually communicate with the SMTP server), which means that the corresponding web server worker thread can handle the next request faster.

privacyIDEA implements a job queue based on `huey`_, which uses a `Redis`_ server to store jobs. Only sending emails can be offloaded to the queue.

Configuration
-------------

The job queue is disabled by default. In order to enable it, add the following configuration option to ``pi.cfg``::

	PI_JOB_QUEUE_CLASS = 'privacyidea.lib.queues.huey_queue.HueyQueue'

After a server restart, you can instruct individual SMTP servers to send all emails via the job queue by checking a corresponding box in the SMTP server configuration (see :ref:`smtpserver`). This means that you can have separate SMTP server configurations, some of which send emails via the job queue, some of which send emails during the request processing.

Note that you need to run a `Redis`_ server that the privacyIDEA server can reach. By default, huey assumes a locally running Redis server. You can use a configuration option to provide a different URL (`see here <https://redis.readthedocs.io/en/stable/connections.html#redis.connection.ConnectionPool.from_url>`_ for information on the URL format)::

	PI_JOB_QUEUE_URL = 'redis://somehost'

In addition to the privacyIDEA server, you will have to run a worker process which fetches jobs from the queue and executes them. You can start it as follows::

	privacyidea-queue-huey

By default, the worker process logs to ``privacyidea-queue.log`` in the current working directory. You can pass a different logfile by using the ``-l`` option::

	privacyidea-queue-huey -l /var/log/queue.log

As the script is heavily based on the huey consumer script, you can find information about additional options in the `huey documentation <https://huey.readthedocs.io/en/latest/consumer.html#options-for-the-consumer>`_.

Note that a side effect of the queue is that the privacyIDEA server does not raise or log errors if an email could not be sent. Hence, it is important to monitor the queue log file for errors.

.. _Redis: https://redis.io/
.. _huey: https://huey.readthedocs.io/en/latest/
