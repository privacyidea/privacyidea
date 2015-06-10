#
#    privacyIDEA, fork of LinOTP (radius_linotp.pm)
#
#    2015-06-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Add using of Stripped-User-Name and Realm from the 
#               RAD_REQUEST
#    2015-04-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               fix typo in log
#    2015-02-25 cornelius kölbel <cornelius@privacyidea.org>
#               remove the usage of simplecheck and use /validate/check
#    2014-06-25 Cornelius Kölbel
#               changed the used modules from Config::Files to Config::IniFile
#		        to make it easily run on CentOS with EPEL, without CPAN
#                      
#    Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
# 
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
# 
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
#
#   Copyright 2002  The FreeRADIUS server project
#   Copyright 2002  Boian Jordanov <bjordanov@orbitel.bg>
#   Copyright 2011  LSE Leading Security Experts GmbH
#
#    E-mail: linotp@lsexperts.de
#    Contact: www.linotp.org
#    Support: www.lsexperts.de




#
# Based on the Example code for use with rlm_perl
#
#

=head1 NAME

freeradius_perl - Perl module for use with FreeRADIUS rlm_perl, to authenticate against 
  LinOTP      http://www.linotp.org
  privacyIDEA http://www.privacyidea.org

=head1 SYNOPSIS

   use with freeradius:  
   
   Configure rlm_perl to work with privacyIDEA:
   in /etc/freeradius/users 
    set:
     DEFAULT Auth-type := perl

  in /etc/freeradius/modules/perl
     point
     perl {
         module = 
  to this file

  in /etc/freeradius/sites-enabled/<yoursite>
  set
  authenticate{
    perl
    [....]

=head1 DESCRIPTION

This module enables freeradius to authenticate using privacyIDEA or LinOTP.

   TODO: 
     * checking of server certificate


=head2 Methods

   * authenticate
   

=head1 CONFIGURATION

The authentication request with its URL and default LinOTP/privacyIDEA Realm 
could be defined in a dedicated configuration file, which is expected to be:

  /opt/privacyIDEA/rlm_perl.ini
  
This configuration file could contain default definition for URL and REALM like
  [Default]
  URL = http://192.168.56.1:5001/validate/check
  REALM =  

But as well could contain "Access-Type" specific configurations, e.g. for the 
Access-Type 'scope1', this would look like:

  [Default]
  URL = https://localhost/validate/check
  REALM =  
  [scope1]
  URL = http://192.168.56.1:5001/validate/check
  REALM = mydefault

=head1 AUTHOR

Cornelius Koelbel (cornelius.koelbel@lsexperts.de)
Cornelius Koelbel (conrelius@privacyidea.org)

=head1 COPYRIGHT

Copyright 2013, 2014

This library is free software; you can redistribute it 
under the GPLv2.

=head1 SEE ALSO

perl(1).

=cut

use strict;
use LWP 6;
use Config::IniFiles;
use Data::Dump;
use Try::Tiny;
use JSON qw( decode_json );


# use ...
# This is very important ! Without this script will not get the filled hashes from main.
use vars qw(%RAD_REQUEST %RAD_REPLY %RAD_CHECK %RAD_CONFIG );

# This is hash wich hold original request from radius
#my %RAD_REQUEST;
# In this hash you add values that will be returned to NAS.
#my %RAD_REPLY;
#This is for check items
#my %RAD_CHECK;


# constant definition for the remapping of return values
use constant RLM_MODULE_REJECT  =>  0; #  /* immediately reject the request */
use constant RLM_MODULE_FAIL    =>  1; #  /* module failed, don't reply */
use constant RLM_MODULE_OK      =>  2; #  /* the module is OK, continue */
use constant RLM_MODULE_HANDLED =>  3; #  /* the module handled the request, so stop. */
use constant RLM_MODULE_INVALID =>  4; #  /* the module considers the request invalid. */
use constant RLM_MODULE_USERLOCK => 5; #  /* reject the request (user is locked out) */
use constant RLM_MODULE_NOTFOUND => 6; #  /* user not found */
use constant RLM_MODULE_NOOP     => 7; #  /* module succeeded without doing anything */
use constant RLM_MODULE_UPDATED  => 8; #  /* OK (pairs modified) */
use constant RLM_MODULE_NUMCODES => 9; #  /* How many return codes there are */

our $ret_hash = { 
    0 => "RLM_MODULE_REJECT",
    1 => "RLM_MODULE_FAIL",
    2 => "RLM_MODULE_OK",
    3 => "RLM_MODULE_HANDLED",
    4 => "RLM_MODULE_INVALID", 
    5 => "RLM_MODULE_USERLOCK",
    6 => "RLM_MODULE_NOTFOUND",
    7 => "RLM_MODULE_NOOP",
    8 => "RLM_MODULE_UPDATED",
    9 => "RLM_MODULE_NUMCODES"
};

## constant definition for comparison
use constant false => 0;
use constant true  => 1;

## constant definitions for logging
use constant Debug => 1;
use constant Auth  => 2;
use constant Info  => 3;
use constant Error => 4;
use constant Proxy => 5;
use constant Acct  => 6;

my $LIN_OK     = ":-)";
my $LIN_REJECT = ":-(";
my $LIN_FAIL   = ":-/";


our $CONFIG_FILE = "/opt/privacyIDEA/rlm_perl.ini";
our $Config = {};
our $cfg_file;

if ( -e $CONFIG_FILE ) {
    $cfg_file = Config::IniFiles->new( -file => $CONFIG_FILE);
    $Config->{FSTAT} = "found!";
    $Config->{URL} = $cfg_file->val("Default", "URL");
    $Config->{REALM}   = $cfg_file->val("Default", "REALM");
    $Config->{RESCONF} = $cfg_file->val("Default", "RESCONF");
    $Config->{Debug}   = $cfg_file->val("Default", "Debug");
    $Config->{SSL_CHECK} = $cfg_file->val("Default", "SSL_CHECK");

}
else {
    $Config->{FSTAT} = "not found!";
    $Config->{URL}     = 'https://127.0.0.1/validate/check';
    $Config->{REALM}   = '';
    $Config->{RESCONF} = "";
    $Config->{Debug}   = "FALSE";
    $Config->{SSL_CHECK} = "FALSE";
}

# Function to handle authenticate
sub authenticate {

    ## show where the config comes from - 
    # in the module init we can't print this out, so it starts here
    &radiusd::radlog( Info, "Config File $CONFIG_FILE ".$Config->{FSTAT} );

    # we inherrit the defaults
    my $URL     = $Config->{URL};
    my $REALM   = $Config->{REALM};
    my $RESCONF = $Config->{RESCONF};
    
    my $debug   = false;
    if ( $Config->{Debug} =~ /true/i ) {
        $debug = true;
    }

    my $check_ssl = false;
    if ( $Config->{SSL_CHECK} =~ /true/i ) {
		$check_ssl = true;
    }

    &radiusd::radlog( Info, "Default URL $URL " );

    # if there exists an auth-type config may overwrite this
    my $auth_type = $RAD_CONFIG{"Auth-Type"};

    try {
	&radiusd::radlog( Info, "Looking for config for auth-type $auth_type");
	if ( ( $cfg_file->val( $auth_type, "URL") )) {
            $URL = $cfg_file->val( $auth_type, "URL" );
        }
	if ( ( $cfg_file->val( $auth_type, "REALM") )) {
            $REALM = $cfg_file->val( $auth_type, "REALM" );
        }  
        if ( ( $cfg_file->val( $auth_type, "RESCONF") )) {
            $RESCONF = $cfg_file->val( $auth_type, "RESCONF" );
        }
      }
      catch {
        &radiusd::radlog( Info, "Warning: $@" );
      };

    if ( $debug == true ) {
        &log_request_attributes;
    }

    my %params = ();

    # put RAD_REQUEST members in the privacyIDEA request
    if ( exists( $RAD_REQUEST{'State'} ) ) {
        my $hexState = $RAD_REQUEST{'State'};
        if ( substr( $hexState, 0, 2 ) eq "0x" ) {
            $hexState = substr( $hexState, 2 );
        }
        $params{'state'} = pack 'H*', $hexState;
    }
    if ( exists( $RAD_REQUEST{'User-Name'} ) ) {
        $params{"user"} = $RAD_REQUEST{'User-Name'};
    }
    if ( exists( $RAD_REQUEST{'Stripped-User-Name'} )) {
        $params{"user"} = $RAD_REQUEST{'Stripped-User-Name'};
    }
    if ( exists( $RAD_REQUEST{'User-Password'} ) ) {
        $params{"pass"} = $RAD_REQUEST{'User-Password'};
    }
    if ( exists( $RAD_REQUEST{'NAS-IP-Address'} ) ) {
        $params{"client"} = $RAD_REQUEST{'NAS-IP-Address'};
    }
    if ( length($REALM) > 0 ) {
        $params{"realm"} = $REALM;
    } elsif ( length($RAD_REQUEST{'Realm'}) > 0 ) {
        $params{"realm"} = $RAD_REQUEST{'Realm'};
    }
    if ( length($RESCONF) > 0 ) {
        $params{"resConf"} = $RESCONF;
    }

    &radiusd::radlog( Info, "Auth-Type: $auth_type" );
    &radiusd::radlog( Info, "url: $URL" );
    &radiusd::radlog( Info, "user sent to privacyidea: $params{'user'}" );
    &radiusd::radlog( Info, "realm sent to privacyidea: $params{'realm'}" );
    &radiusd::radlog( Info, "resolver sent to privacyidea: $params{'resConf'}" );
    &radiusd::radlog( Info, "client sent to privacyidea: $params{'client'}" );
    &radiusd::radlog( Info, "state sent to privacyidea: $params{'state'}" );
    if ( $debug == true ) {
        &radiusd::radlog( Debug, "urlparam $_ = $params{$_}\n" )
          for ( keys %params );
    }
    else {
        &radiusd::radlog( Info, "urlparam $_ \n" ) for ( keys %params );
    }

    my $ua     = LWP::UserAgent->new();
	if ($check_ssl == false) {
		try {
			# This is only availble with with LWP version 6
        		&radiusd::radlog( Info, "Not verifying SSL certificate!" );
			$ua->ssl_opts( verify_hostname => 0, SSL_verify_mode => 0x00 );
		} catch {
		        &radiusd::radlog( Error, "ssl_opts only supported with LWP 6. error: $@" );
		}
	}
    my $response = $ua->post( $URL, \%params );
    my $content  = $response->decoded_content();
    if ( $debug == true ) {
        &radiusd::radlog( Debug, "Content $content" );
    }
    $RAD_REPLY{'Reply-Message'} = "privacyIDEA server denied access!";
    my $g_return = RLM_MODULE_REJECT;

    if ( $response->is_success ) {
        # This was an OK 200 response
        my $decoded = decode_json( $content );
        my $message = $decoded->{detail}{message};
        if ( $decoded->{result}{value} ) {
            &radiusd::radlog( Info, "privacyIDEA access granted" );
            $RAD_REPLY{'Reply-Message'} = "privacyIDEA access granted";
            $g_return = RLM_MODULE_OK;
        }
        elsif ( $decoded->{result}{status} ) {

            if ( $decoded->{detail}{transaction_id} ) {
                ## we are in challenge response mode:
                ## 1. split the response in fail, state and challenge
                ## 2. show the client the challenge and the state
                ## 3. get the response and
                ## 4. submit the response and the state to linotp and
                ## 5. reply ok or reject
                $RAD_REPLY{'State'} = $decoded->{detail}{transaction_id};
                $RAD_REPLY{'Reply-Message'} = $decoded->{detail}{message};
                $RAD_CHECK{'Response-Packet-Type'} = "Access-Challenge";
                $g_return  = RLM_MODULE_HANDLED;
            } else {
                &radiusd::radlog( Info, "privacyIDEA access denied" );
                #$RAD_REPLY{'Reply-Message'} = "privacyIDEA access denied";
                $RAD_REPLY{'Reply-Message'} = $decoded->{detail}{message};
                $g_return = RLM_MODULE_REJECT;
            }
        }


    } else {
        my $status = $response->status_line;
        &radiusd::radlog( Info, "privacyIDEA request failed: $status" );
        $RAD_REPLY{'Reply-Message'} = "privacyIDEA request failed: $status";
        $g_return = RLM_MODULE_FAIL;
    }
    &radiusd::radlog( Info, "return $ret_hash->{$g_return}" );
    return $g_return;

}

sub log_request_attributes {

    # This shouldn't be done in production environments!
    # This is only meant for debugging!
    for ( keys %RAD_REQUEST ) {
        &radiusd::radlog( Debug, "RAD_REQUEST: $_ = $RAD_REQUEST{$_}" );
        ;
    }

}

# Function to handle authorize
sub authorize {

    # For debugging purposes only
    # &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle preacct
sub preacct {

    # For debugging purposes only
    #       &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle accounting
sub accounting {

    # For debugging purposes only
    #       &log_request_attributes;

    # You can call another subroutine from here
    &test_call;

    return RLM_MODULE_OK;
}

# Function to handle checksimul
sub checksimul {

    # For debugging purposes only
    #       &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle pre_proxy
sub pre_proxy {

    # For debugging purposes only
    #       &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle post_proxy
sub post_proxy {

    # For debugging purposes only
    #       &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle post_auth
sub post_auth {

    # For debugging purposes only
    #       &log_request_attributes;

    return RLM_MODULE_OK;
}

# Function to handle xlat
sub xlat {

    # For debugging purposes only
    #       &log_request_attributes;

    # Loads some external perl and evaluate it
    my ( $filename, $a, $b, $c, $d ) = @_;
    &radiusd::radlog( 1, "From xlat $filename " );
    &radiusd::radlog( 1, "From xlat $a $b $c $d " );
    local *FH;
    open FH, $filename or die "open '$filename' $!";
    local ($/) = undef;
    my $sub = <FH>;
    close FH;
    my $eval = qq{ sub handler{ $sub;} };
    eval $eval;
    eval { main->handler; };
}

# Function to handle detach
sub detach {

    # For debugging purposes only
    #       &log_request_attributes;

    # Do some logging.
    &radiusd::radlog( 0, "rlm_perl::Detaching. Reloading. Done." );
}

#
# Some functions that can be called from other functions
#

sub test_call {

    # Some code goes here
}

1;
