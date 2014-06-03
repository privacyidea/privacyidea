'''
privacyIDEA is an open solution for strong two-factor authentication with One Time Passwords.

The core modules and basic necessary components are licensed under the AGPLv3, so that you 
are able to have a complete working open source solution. But privacyIDEA is also open as far 
as its modular architecture is concerned.   
privacyIDEA aims to not bind you to any  decision of the authentication protocol or it does not 
dictate you where your user information should be stored. This is achieved by its new, totally 
modular architecture. 

The modules are:

Tokenclasses
------------

    privacyIDEA already comes with several tokenclasses defined in privacyidea.lib.tokenclass.py
    But you can simply define your own tokenclass object. Take a look at the base class
    in tokenclass.py
    
UserIdResolvers
---------------
    
Controllers
===========
    privacyIDEA runs as a web application, so you may communitcate with privacyIDEA using 
    web calls.
    
Authentication Interface
------------------------
    user the controller /validate/....

Admin interface
---------------
    use the controller /admin/....
'''