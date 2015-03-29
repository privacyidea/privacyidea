This module is to be used with http://pam-python.sourceforge.net/.

To be used like this::

   requisite    pam_python.so /path/to/modules/privacyidea-pam.py

It can take the following parameters:

url=https://your-server 

   default is https://localhost
  
debug

   write debug information to the system log
   
realm=<realm>

   pass additional realm to privacyidea
   
nosslverify

   Do not verify the SSL certificate
   
prompt

   The password prompt. Default is "Your OTP".
