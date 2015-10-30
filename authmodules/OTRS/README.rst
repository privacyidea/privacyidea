This authentication module adds two factor authentication with privacyIDEA
to OTRS.

Installation
============

Simply copy the the ``privacyIDEA.pm`` into the ``Auth`` directory. Usually located at
``/opt/otrs/Kernel/System/Auth``.

Configuration
=============

You need to activate the privacyIDEA authentication module and you
need to specify where the privacyIDEA server is located and whether you want to 
check the validity of the SSL certificate.

You can do this in ``Kernel/Config.pm`` like this::
 
    $Self->{'AuthModule'} = 'Kernel::System::Auth::privacyIDEA';
    $Self->{'AuthModule::privacyIDEA::URL'} = \
             "https://localhost/validate/check";
    $Self->{'AuthModule::privacyIDEA::disableSSLCheck'} = "yes";


