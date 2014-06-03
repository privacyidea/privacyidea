# --
# Kernel/System/Auth/privacyIDEA.pm - provides the OTP authentication
# Copyright (C) 2014 Cornelius Koelbel
# --
# This software comes with ABSOLUTELY NO WARRANTY. For details, see
# the enclosed file COPYING for license information (AGPL). If you
# did not receive this file, see http://www.gnu.org/licenses/agpl.txt.
# --
package Kernel::System::Auth::privacyIDEA;

use strict;
use warnings;
use LWP;

sub new {
    my ( $Type, %Param ) = @_;

    # allocate new hash for object
    my $Self = {};
    bless( $Self, $Type );

    # check needed objects
    for (qw(LogObject ConfigObject DBObject UserObject GroupObject EncodeObject)) {
        $Self->{$_} = $Param{$_} || die "No $_!";
    }

    # Debug 0=off 1=on
    $Self->{Debug} = 0;

    # get privacyIDEA prefs
    # Something like http://privacy.idea.com/validate/simplecheck
    if ( $Self->{ConfigObject}->Get( 'AuthModule::privacyIDEA::URL') ) {
        $Self->{URL} = $Self->{ConfigObject}->Get( 'AuthModule::privacyIDEA::URL' );
    }
    else {
        $Self->{LogObject}->Log(
            Priority => 'error',
            Message  => "Need AuthModule::privacyIDEA in Kernel/Config.pm",
        );
        return;
    }
    $Self->{realm}
        = $Self->{ConfigObject}->Get( 'AuthModule::privacyIDEA::Realm') || '';
    $Self->{resolver}
        = $Self->{ConfigObject}->Get( 'AuthModule::privacyIDEA::Resolver') || '';
    return $Self;
}

sub GetOption {
    my ( $Self, %Param ) = @_;

    # check needed stuff
    if ( !$Param{What} ) {
        $Self->{LogObject}->Log( Priority => 'error', Message => "Need What!" );
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
            $Self->{LogObject}->Log( Priority => 'error', Message => "Need $_!" );
            return;
        }
    }
    $Param{User} = $Self->_ConvertTo( $Param{User}, 'utf-8' );
    $Param{Pw}   = $Self->_ConvertTo( $Param{Pw},   'utf-8' );

    # get params
    my $RemoteAddr = $ENV{REMOTE_ADDR} || 'Got no REMOTE_ADDR env!';

    # remove leading and trailing spaces
    $Param{User} =~ s/^\s+//;
    $Param{User} =~ s/\s+$//;

    my $ua = LWP::UserAgent->new();
    my $req = HTTP::Request->new(GET => $Self->{URL} . "?user=" .
	        $Param{User} . "&pass=" . 
	        $Param{Pw} );
    my $response = $ua->request( $req );

    die "Error at $Self->{URL}\n ", $response->status_line, "\n Aborting"
      unless $response->is_success;
      
    if($response->content =~ m/:\-\)/i) {
		$success = $Param{User};
    }

    # return login
    return $success;

}


sub _ConvertTo {
    my ( $Self, $Text, $Charset ) = @_;

    return if !defined $Text;

    if ( !$Charset || !$Self->{DestCharset} ) {
        $Self->{EncodeObject}->EncodeInput( \$Text );
        return $Text;
    }

    # convert from input charset ($Charset) to directory charset ($Self->{DestCharset})
    return $Self->{EncodeObject}->Convert(
        Text => $Text,
        From => $Charset,
        To   => $Self->{DestCharset},
    );
}

sub _ConvertFrom {
    my ( $Self, $Text, $Charset ) = @_;

    return if !defined $Text;

    if ( !$Charset || !$Self->{DestCharset} ) {
        $Self->{EncodeObject}->EncodeInput( \$Text );
        return $Text;
    }

    # convert from directory charset ($Self->{DestCharset}) to input charset ($Charset)
    return $Self->{EncodeObject}->Convert(
        Text => $Text,
        From => $Self->{DestCharset},
        To   => $Charset,
    );
}


1;
