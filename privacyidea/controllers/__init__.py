'''
privacyIDEA is an open solution for strong two-factor authentication with One Time Passwords.

The core modules and basic necessary components are licensed under the AGPLv3, so that you 
are able to have a complete working open source solution. But privacyIDEA is also open as far 
as its modular architecture is concerned.   
privacyIDEA aims to not bind you to any  decision of the authentication protocol or it does not 
dictate you where your user information should be stored. This is achieved by its new, totally 
modular architecture. 

This is the controller module. The controllers provide the Web API to communicate with privacyIDEA.

You can use the following controllers:

account		- used for loggin in to the selfservice
admin		- API to manage the tokens
audit		- to search the audit trail
auth		- to do authentication tests
error		- to display errors
gettoken	- to retrieve OTP values
license		- to manage license
manage		- the Web UI
openid		- the openid interface
selfservice	- the selfservice UI
system		- to configure the system
testing		- for testing purposes
validate	- for authenticating/ OTP checking


'''

