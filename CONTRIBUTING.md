# You are welcome to contribute to privacyIDEA

There are different ways to contribute. Some of them should
be really easy.

First of all:  
**Thanks a lot for contributing to privacyIDEA!**

## Talk about it

You are using privacyIDEA in your network? Talk about it!
Write a blog post, tell your friends or simply twitter about it.
This will make privacyIDEA wider known and attract new users and contributors.

## Talk to us

You may join talking in the privacyIDEA Forum.
Talk to other users and share your experience!

https://community.privacyidea.org

### A word about community

Community does not mean that some developers are responsible
for solving all your problems. Read the AGPL!
**THIS SOFTWARE COMES WITH NO WARRANTY**

As soon as you start using privacyIDEA you are becoming part of
the community and this also comes with some kind of responsibility.
So you can make privacyIDEA better and earn karma points by
sharing your experience and helping other, younger users.

By doing so the developers have more time to develop and
improving your beloved project.

So **you are "the community"**, go and help others!

https://community.privacyidea.org

## Long Term Supported Versions
We currently do **not** have a long term supported versions. If a new minor version is released, 
the previous minor versions will usually not receive any more updates.

## Professional services

If you want to get rid of the NO-WARRANTY
label take a look at privacyIDEA Enterprise Edition including a
Service Level Agreement or get professional consultancy:

- Consultancy
  https://netknights.it/en/leistungen/one-time-services/
- privacyIDEA Enterprise Edition
  https://netknights.it/en/leistungen/service-level-agreements/


## Tell us your ideas

If you have a *new idea* you may submit a feature request.
This should be a new idea that puts forward privacyIDEA and looks
at some things from a new angle.

Submit an issue and describe your idea in the best possible details.

https://github.com/privacyidea/privacyidea/issues

## Documentation

The source code is pretty well documented. The main documentation resides in the
`doc`-subfolder and can be build with:
```
pip install -r doc/requirements.txt
cd doc/ && make html
```
This also pulls the API-documentation from the source code.
The latest release documentation can be found here:

http://privacyidea.readthedocs.io/en/latest/

## Translations

If you have no programming skills you can still get involved
directly with the software by providing translations into
different languages.

You can do it easily without technical skills in your browser at
weblate.org https://hosted.weblate.org/engage/privacyidea/.

Or use your own system:

http://privacyidea.readthedocs.io/en/latest/faq/translation.html

## Test coverage

We aim to have the highest test coverage possible, but tests can always be
improved.

The tests are also split into three layers: database, library and API.
Here you can find files that should get an improved test coverage.
Take a look at yellow and red files.

https://codecov.io/github/privacyidea/privacyidea?branch=master

## Report a security vulnerability

If you found a problematic security vulnerability, please
refrain from reporting an issue at GitHub but send this vulnerability to
us directly.
Please include the following details:

* The name and version of the problematic software component,
  and if possible

  * the location of the issue and
  * the potential impact

* A detailed description to reproduce the vulnerability and

* Your name, (handle or alias) to be included in the
  disclosure and hall of fame.

You can send this information to the privacyIDEA core development team by
sending an email to

   security@privacyidea.org

or, if you want to stay anonymous/pseudonymous, you can upload your information
to

   https://lancelot.netknights.it/owncloud/s/a6sVvOT0Fb3utd9

Thanks a lot for your support and your discretion.

## Develop

And of course you can contribute code! Starting with fixes in the
code or even implementations of new concepts.
Take a look at the issues. Maybe you can find something, you
would like to start with?
If you are sending a pull request, please note the following:

* Before coding you need to **create an issue**, that describes
  your problem or idea, which you want to solve with your
  pull request. We want to discuss the functionality within the issue and
  not guess the intention from the pull request!
* In your pull request, refer to the issue.
* Try to use an expressive commit message and describe the changes you made in the commit or in the issue.
* We try to stick to **PEP 8**. So please use sensible names, check your line
  breaks, comment your classes and functions...
  Using something like *pylint* or an integrated editor like *pycharm* can
  help you with that.
* When implementing something new, try to do more with **less code**!
* When implementing something new, try to implement it in a **generic way**,
  that it can be used and different use cases.
* We are proud of our **code coverage**. The modular code with decorators can
  be tested easier. Write **tests** for your code!
* If you need to change the database model, edit ``privacyidea/models.py``
  accordingly. Then you can use
  ``./pi-manage`` to create migration scripts. The migration scripts
  are located at ``migrations/versions/``.
  To create a migration script to update the database schema run:

  ```
  ./pi-manage db migrate
  ```

  This will create a new file in ``migrations/versions/``. Edit the description
  and put a *try-except* around the operations. Take a look at the other
scripts.
  Then you can run:

  ```
  ./pi-manage db upgrade
  ```

  To update the local database.

## Development Workflow

The following section describes our development workflow: How do we handle
issues, how do we develop privacyIDEA, how do we perform code reviews?

### Terminology

In the following, *"we"* and *"team"* refers to the [privacyIDEA development
team](https://github.com/orgs/privacyidea/people). *"External contributors"*
refers to contributing developers from the community.

### Issues

##### Issue Templates

We encourage external contributors to use one of the predefined issue templates
for bugs and feature requests. In case of bug reports, external contributors as
well as team members should describe their top-level intent, the expected
behavior of the system, its actual behavior, and the steps taken to produce it.

##### Assigning Issues

The team member assigned to an issue is responsible for working on it, creating
a pull request and getting the pull request reviewed and merged.

##### Milestones

For each planned release, we create a GitHub milestone. We add issues to
milestones in order to keep track of features that should be implemented or
bugs that should be fixed for the respective release. This also helps with
creating the release changelog later.

### Projects

We use *GitHub Projects* to organize our weekly development cycle.

In a weekly meeting we decide, which issues will be handled during the
following week. Issues are put into the
[project](https://github.com/privacyidea/privacyidea/projects) in the state
*Todo*. It is best to create an issue for your contribution, because we track issues and not pull requests.

When a developer starts working on the issue, the developer puts the issue
into the state *In progress*. When he is done he opens a pull requests,
assigns a reviewer and puts the issue into the state *Review in progress*.

When the reviewer is happy with the pull request, he can merge the PR
into the master branch. The issue is closed and goes into the state
*Nearly done*.

The closes issue is again discussed in the next meeting and then finally
moved to the state *Done*. Alternatively, if the merged pull request was not sufficient or additional requirements
come up, the issue is moved back to *In progress*.

(More details on each step further below)

### Branches

##### ``master`` branch

Our ``master`` branch represents the current development state and, as a
consequence, may be unstable. Features are usually added there.

##### Stable branches

For each minor version ``X.Y`` (e.g. 2.23, 3.0, ...), we create a *stable
branch* called ``branch-X.Y``, e.g.
[``branch-3.0``](https://github.com/privacyidea/privacyidea/tree/branch-3.0).
Hotfixes for stable versions are usually added to the stable branches. Stable
branches are then merged back into the master branch.

##### Local Branches and Pull Requests

We do not directly work on the ``master`` branch or the stable branches.
Instead, we locally create new branches, diverging either from ``master`` or a
stable branch. These branches are called ``123/some-shortname``, where ``123``
refers to an issue number, and ``some-shortname`` is a short description of the
changes. If we are done developing a bugfix, a feature, or a reasonable part of
a feature, we open a pull request (see below).

### Pull Requests and Code Reviews

##### PR descriptions

We use GitHub's *pull requests*. The pull request description mentions the
issue that is being worked on (e.g. "Working on #xyz" or "Closes #xyz", see
[keywords](https://help.github.com/en/articles/closing-issues-using-keywords)).
The respective issue should be added to a milestone. This makes it easier to
put together changelogs for new releases.

##### Code Reviews

We perform code reviews. Each pull request is reviewed by one or more team
members before it is merged.

##### Choosing a Reviewer

In the following, we call the requester of a pull request the *developer* and
differentiate between *external contributors* and *team members*:

* An external contributor can simply open a pull request. The team then decides
on a reviewer and accordingly requests a review. If there was a discussion in the issue before, it can be sensible to
request a review from the team member who was involved in the discussion.
* A team member explicitly requests a review from one or more other team
members. In order to find a suitable reviewer, a developer may refer to the
[development team list](Development-Team). Even after having created a pull
request, the **developer is responsible for getting the pull request merged**.
In particular, it is the developer's responsibility to choose a suitable
reviewer. As the reviewer may not notice an incoming review request due to the
high number of notifications, the developer is responsible for reminding the
reviewer of pending review requests. If the reviewer is too busy to deal with
the pull request, the developer chooses a different reviewer.

We *do not* request reviews from the whole team, because this makes it hard to
assign responsibility.

##### Reviewing Pull Requests

The reviewer uses the GitHub [code review
features](https://github.com/features/code-review/) to add comments and request
changes. The developer addresses the remarks in the following commits and
replies to the comments. If the reviewer is satisfied with the changes and/or explanations, the
reviewer resolves the respective conversation. If the reviewer added a simple comment, e.g. about a typo, 
the developer can resolve the conversation after fixing it.

##### Merging a Pull Request

If the reviewer approves a pull request, and if no other reviews have been
requested (see below), the reviewer should merge (or rebase or squash and
merge) the pull request. When the pull request is merged, the reviewer deletes
the feature branch, if possible.

##### Multiple Reviewers

The developer may also request reviews from multiple team members. This makes
sense if the PR spans across multiple architectural layers (e.g. backend *and*
frontend), or if the developer wants both a functional (does the PR fix the
bug?) and technical review (is the code okay?). If a developer requests
multiple reviews, the PR description should explicitly state if *all* reviews
should be positive, or if *one* positive review is sufficient.
