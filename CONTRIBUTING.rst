You are welcome to contribute to privacyIDEA
============================================

There are different ways to contribute. Some of them should
be really easy.

**Thanks a lot for contributing to privacyIDEA!**

Tell about it
-------------

You are using privacyIDEA in your network? Tell about it!
Write a blog post, tell your friends or simply twitter about it.
This will make privacyIDEA wider known and attract new contributors.

Talk to us
----------

You may join talking in the privacyIDEA Forum.
Talk to other users and share your experience!

https://community.privacyidea.org

A word about community
~~~~~~~~~~~~~~~~~~~~~~

Community does not mean that some developers are responsible
for solving all your problems. Read the AGPL! 
**THIS SOFTWARE COMES WITH NO WARRANTY**

As soon as you start using privacyIDEA you are becoming part of
the community and this also comes with some kind of responsibility.
So you can make privacyIDEA better and earn karma points by
sharing your experience and helping other, younger users.

By doing so the developers have more time to develop and 
improving your beloved project and hopefully allowing
the developers to earn some money to make a living.

So **you are "the community"**, go and help others!

https://community.privacyidea.org

Money
-----

This is an important part to contribute to privacyIDEA.
To allow developers to work full time on privacyIDEA they
have to make money. 

One possibility to do this and also get rid of the NO-WARRANTY 
label is to get privacyIDEA Enterprise Edition including a
Service Level Agreement or corresponding consultancy.

- consultancy 
  https://netknights.it/en/leistungen/one-time-services/
- privacyIDEA Enterprise Edition 
  https://netknights.it/en/leistungen/service-level-agreements/


Tell us your ideas
------------------

If you have a *new idea* you may submit a feature request.
This should be a new idea that puts forward privacyIDEA and looks 
at some things from a new angle. 

Submit an issue and describe your idea in the best possible details.

https://github.com/privacyidea/privacyidea/issues

Translations
------------

If you have no programming skills you can still get involved
directly with the software by providing translations into 
different languages.

http://privacyidea.readthedocs.io/en/latest/faq/translation.html?highlight=translate

Test coverage
-------------

We have a rather high test coverage. But tests can always be
improved.

The tests are also split in three levels: database, library and API.
Here you can find files that should get an improved test coverage.
Take a look at yellow and red files.

https://codecov.io/github/privacyidea/privacyidea?branch=master

Develop
-------

And of course you can contribute code! Starting with fixings in the
code or even implementations of new concepts.
Take a look at the issues. Maybe you can find something, you
would like to start with?
If you are sending a pull request, please note the following:

* often it is a good idea to **create an issue**, that describes
  you problem or idea, which you want to solve with your
  pull request.
* in your pull request refer to the issue.
* describe your changes in the commit message.
* At the beginning of the file, add the date, your name,
  your email address and a description of what you 
  changed in the file!
* If you need to change the database model, edit ``privacyidea/models.py``
  accordingly. Then you can use
  ``./pi-manage`` to create migration scripts. The migration scripts
  are located at ``migrations/versions/``.
  To create a migration script to update the database schema run:

      ./pi-manage db migrate

  This will create a new file in ``migrations/versions/``. Edit the description
  and put a *try-except* around the operations. Take a look at the other scripts.
  Then you can run:

      ./pi-manage db upgrade

  To update the local database.

Contribution Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

Git Handling
............

* privacyIDEA is developed on **github**.
  The current development is performed on the
  **master** branch.
  So the master branch can be unstable!
* For every stable release we set a **tag** like **v2.17**. There can be
  other tags like *v2.18dev1*, these are tags during development and should
  not be used productively.
* If a released stable version needs fixes, we open a **release branch** like
  **branch-2.16**. In this branch patch versions like 2.16.1 will be
  developed according to *semantic versioning*.
* When developing a feature there *should* be an **issue** for that.
* Your **commit message** or pull request should refer to this issue.
* When providing a **pull request** please check if it makes sense to
  **squash your commits**.
* If the development of a task will probably need more time and consist of
  more than one commit, you should use a **feature branch**.

Code
....

* We try to stick to **PEP 8**. So please use sensible names, check your line
  breaks, comment your classes and functions...
  Using something like *pylint* or an integrated editor like *pycharm* can
  help you with that.
* When implementing something new, try to do more with **less code**!
* When implementing something new, try to implement it in a **generic way**,
  that it can be used and different use cases.
* We are proud of our **code coverage**. The modular code with decorators can
  be tested more easy. Write **tests** for your code!


