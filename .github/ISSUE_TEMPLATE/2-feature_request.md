---
name: Feature request
about: Suggest an idea for this project - plan a new development
title: ''
labels: 'Type: Feature request'
assignees: ''

---

**Is your feature request related to a problem? Please describe.**

What are you trying to achieve?

**Describe the solution you'd like**

A clear and concise description of what you want to happen.

**Describe alternatives you've considered**

A clear and concise description of any alternative solutions or features you've considered.

**Additional context**

Add any other context or screenshots, that might help us to better understand your idea, your need and your circumstances.

For privacyIDEA developers. Describe and document the development plans:

# Top level requirements and scenarios

*Describe what needs to be achieved and how the scenario looks like*

*If sensible use a checklist to check, which requirements have been covered by your implementation!*

* [ ] We need to ensure that...
* [ ] Administrators must be able to...

# Implementation

*Describe your implementation plans - what you are exactly going to implement. Use references/link to the existing code*

*Cover the following aspects:*

## Database

Describe the database table that will be added. Define the `name` of the table and the `names of the columns`.

Define, if you need to add a DB migration script.

## Library and API

Describe what needs to be implemented, preferrably also in which files.

Use example code of what you plan to implement:

~~~~Python
new_feature = [ x.name for x in some_return_values if x.id > 0 ]
~~~~

# TODOs

*In the TODO section you can add all steps that need to be implemented*

**USE CHECKLISTS, THESE WILL BE VISIABLE AS TASKS!**

* [ ] add DB table `name` in `models.py`
* [ ] create above mentioned migration script.
* ~~[ ] there might be an aspect that is not relevant anymore~~
* [ ] e.g. Add util function to...
* [ ] e.g. add REST API...
* [ ] e.g. we need to add policy and implement it in e.g. `prepolicy`
  - scope: admin
  - action: new_action_name
  - ...    

Use further checkboxes for

* [ ] add documentation
* [ ] implement tests
