# --
# Kernel/System/Auth/privacyIDEA.pm - provides the OTP authentication
# Copyright (C) 2015 Cornelius Koelbel
#
#  2016-08-31 Cornelius Koelbel <cornelius.koelbel@netknights.it>
#             Add user-agent OTRS to request.
# --
# This software comes with ABSOLUTELY NO WARRANTY. For details, see
# the enclosed file COPYING for license information (AGPL). If you
# did not receive this file, see http://www.gnu.org/licenses/agpl.txt.
#
# This module is to be used with OTRS 4.0
#
# Configure the following in your Kernel/Config.pm:
#    $Self->{'AuthModule'} = 'Kernel::System::Auth::privacyIDEA';
#    $Self->{'AuthModule::privacyIDEA::URL'} = \
#             "https://localhost/validate/check";
#    $Self->{'AuthModule::privacyIDEA::disableSSLCheck'} = "yes";
#
# --
package Kernel::System::Auth::privacyIDEA;

use strict;
use warnings;
use LWP;
use JSON qw( decode_json );

our @ObjectDependencies = (
    'Kernel::Config',
    'Kernel::System::Log',
);

sub new {
    my ( $Type, %Param ) = @_;

    # allocate new hash for object
    my $Self = {};
    bless( $Self, $Type );

    # Debug 0=off 1=on
    $Self->{Debug} = 0;
    # get config object
    my $ConfigObject = $Kernel::OM->Get('Kernel::Config');

    # Something like http://privacy.idea.com/validate/check
    if ( $ConfigObject->Get( 'AuthModule::privacyIDEA::URL') ) {
        $Self->{URL} = $ConfigObject->Get( 'AuthModule::privacyIDEA::URL' );
    }
    else {
        $Kernel::OM->Get('Kernel::System::Log')->Log(
            Priority => 'error',
            Message  => "Need AuthModule::privacyIDEA in Kernel/Config.pm",
        );
        return;
    }
    $Self->{realm}
        = $ConfigObject->Get( 'AuthModule::privacyIDEA::Realm') || '';
    $Self->{resolver}
        = $ConfigObject->Get( 'AuthModule::privacyIDEA::Resolver') || '';
    # Set checSSL = "0", to not check ssl
    $Self->{disableSSL}
        = $ConfigObject->Get( 'AuthModule::privacyIDEA::disableSSLCheck');
    return $Self;
}

sub GetOption {
    my ( $Self, %Param ) = @_;

    # check needed stuff
    if ( !$Param{What} ) {
        $Kernel::OM->Get('Kernel::System::Log')->Log(
            Priority => 'error',
            Message  => "Need What!"
        );
        return;
    }

    # module options
    my %Option = ( PreAuth => 0, );

    # return option
    return $Option{ $Param{What} };
}


sub Auth {
    my ( $Self, %Param ) = @_;

    my $success = "";
    # check needed stuff
    for (qw(User Pw)) {
        if ( !$Param{$_} ) {
            $Kernel::OM->Get('Kernel::System::Log')->Log(
                Priority => 'error',
                Message => "Need $_!" );
            return;
        }
    }

    # get params
    my $RemoteAddr = $ENV{REMOTE_ADDR} || 'Got no REMOTE_ADDR env!';

    # remove leading and trailing spaces
    $Param{User} =~ s/^\s+//;
    $Param{User} =~ s/\s+$//;

    my %http_params = ();
    $http_params{'user'} = $Param{User};
    $http_params{'pass'} = $Param{Pw};
    if ($Self->{realm}) {
        $http_params{'realm'} = $Self->{realm};
    }
    if ($Self->{resolver}) {
        $http_params{'resolver'} = $Self->{resolver};
    }

    my $ua = LWP::UserAgent->new();
    # Set the user-agent to be fetched in privacyIDEA Client Application Type
    $ua->agent("OTRS");
    if ($Self->{disableSSL}) {
        $ua->ssl_opts( verify_hostname => 0, SSL_verify_mode => 0x00 );
    }
    my $response = $ua->post( $Self->{URL}, \%http_params );
    my $content = $response->decoded_content();
    my $decoded = decode_json( $content );

#    my $rcode = $response->code;
#    $Kernel::OM->Get('Kernel::System::Log')->Log(
#                Priority => 'error',
#                Message  => "Response code: $rcode!"
#    );

    if ($response->is_success) {
        if ($decoded->{result}{value}) {
            $success = $Param{User};
        } else {
            my $message = $decoded->{detail}{message};
            my $user = $Param{User};
            $Kernel::OM->Get('Kernel::System::Log')->Log(
                    Priority => 'error',
                    Message  => "$user can not authenticate: $message"
            );
        }
    } else {
        my $statusline = $response->status_line;
        $Kernel::OM->Get('Kernel::System::Log')->Log(
                Priority => 'error',
                Message  => "Response: $statusline!"
        );
    }

    # return login
    return $success;
}

1;
