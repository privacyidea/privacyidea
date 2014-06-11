# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#    
'''
  Description:  This module can be used to create the optical challenge image for Feitian
                c601 token.
                
                c601:
                Either you can create a single challenge that will display the OTP response
                    calculate_optical_data(value="12345678")
                
                or you can split the challenge into ACCOUNT and AMOUNT.
                     calculate_optical_data(value="12345", type=ACCOUNT)
                     calculate_optical_data(value="67890", type=AMOUNT)
                     
                The challenge then will be AMOUNT+ACCOUNT (6789012345)
                     
            FIXME: should be moved to the token definition
                 
'''
CHALLENGE = [0, 1]
ACCOUNT = [1, 1]
AMOUNT = [1, 0]

DELAY_BLACK = 5
DELAY_WHITE = 5
DELAY_GRAY = 5

def _calculate_sum(value):
    sum = 0;
    alternate = True;

    for c in value:
        n = ord(c) & 0x0f

        if alternate:
            v = n * 2
            if v > 9:
                sum += 1 + (v % 10)
            else:
                sum += v
            alternate = False
        else:
            sum += n
            alternate = True

    return (10 - (sum % 10)) % 10

def _modify_optical(optical):
    '''
    Takes the optical array and modifies it to the three 
        black = 0
        gray =  1
        white = 2
        values
    '''
    ret_optical = []
    t = 0
    ret_optical.append(t)

    for o in optical[:-1]:
        if o == 1:
            t = t + 1
            if t > 2:
                t = 0
        else:
            t = t - 1
            if t < 0:
                t = 2

        ret_optical.append(t)

    return ret_optical

def calculate_optical_data(value="", type=CHALLENGE):
    ''' create an array, representing black and white (1 and 0)
    
    type
        0,1 : Default challenge
        1,1 : Account
        1,0 : Amount
        
    value
        Input challenge Data: A numerical string
    '''

    # sanity checks
    if len(type) != 2:
        raise Exception("The type is limited to a length of 2.")

    value_int = int(value)

    if type == CHALLENGE:
        if len(value) > 59:
            raise Exception("The length of the challenge value is limited to 59.")

        if len(value) < 8:
            raise Exception("The length of the challenge value must be a minimum of 8.")

    if type == ACCOUNT or type == AMOUNT:
        if len(value) > 6:
            raise Exception("You should not use amount or account longer than 6, as it will not be displayerd.")

    optical = []

    # header
    optical.append(1)
    optical.append(1)
    optical.append(1)
    optical.append(1)
    optical.append(1)
    optical.append(0)

    # type
    optical.append(type[0])
    optical.append(type[1])

    # Length
    L = "%02d" % len(value)

    # convert a "9" to a binary 1001
    # Lenght
    for c in L:
        optical.append(ord(c) >> 3 & 0x01)
        optical.append(ord(c) >> 2 & 0x01)
        optical.append(ord(c) >> 1 & 0x01)
        optical.append(ord(c) & 0x01)

    # data
    for v in value:
        optical.append(ord(v) >> 3 & 0x01)
        optical.append(ord(v) >> 2 & 0x01)
        optical.append(ord(v) >> 1 & 0x01)
        optical.append(ord(v) & 0x01)

    # checksum
    # sum 0011 - 3 0010 - 2 0001 - 1
    bin = int("%d%d" % (type[0], type[1]))
    bin_str = "%d" % bin

    # type + len + value
    sum_data = bin_str + L + value

    sum = _calculate_sum(sum_data)

    optical.append(sum >> 3 & 0x01)
    optical.append(sum >> 2 & 0x01)
    optical.append(sum >> 1 & 0x01)
    optical.append(sum & 0x01)

    optical = _modify_optical(optical)

    return optical

def _create_image(optical, outfile="challenge.gif", delay=(DELAY_WHITE, DELAY_GRAY, DELAY_BLACK)):
    '''
    Creates an animated GIF for the given data array
    which is the output of calculate optical data
    '''
    input_files = ""
    for o in optical:
        if o == 2:
            input_files += " -delay %d white.gif " % delay[0]
        elif o == 1:
            input_files += " -delay %d gray.gif " % delay[1]
        elif o == 0:
            input_files += " -delay %d black.gif  " % delay[2]
    command = "convert  %s  -loop 0 %s" % (input_files, outfile)
    os.system(command)

if __name__ == '__main__':
    import os

    # data for challenge 12345678
    demo_data_challenge = [ 0, 1, 2, 0, 1, 2, 1, 0, 1, 0, 2, 1, 0, 1, 0, 2, 1, 0, 2, 1, 2, 1, 0, 1, 0, 2, 1, 2, 0, 2, 0, 2, 1, 0, 1, 0, 1, 0, 1, 2, 1, 0, 1, 2, 0, 1, 0, 2, 1, 0, 2, 0]
    optical = calculate_optical_data(value="12345678")
    print "-" * 70
    print "Cha D: %s" % demo_data_challenge
    print "Cha O: %s " % optical
    _create_image(optical)

    # data for account 12345
    demo_data_account = [0, 1, 2, 0, 1, 2, 1, 2, 0, 2, 1, 0, 2, 1, 2, 1, 2, 1, 0, 2, 0, 2, 1, 2, 1, 0, 2, 0, 1, 0, 1, 0, 2, 1, 2, 1, 2, 1, 2, 0]
    optical = calculate_optical_data(value="12345", type=ACCOUNT)
    print "-" * 70
    print "Acc D: %s" % demo_data_account
    print "Acc O: %s " % optical
    _create_image(optical, outfile="account.gif")

    # data for amount
    demo_data_amount = [0, 1, 2, 0, 1, 2, 1, 2, 1, 0, 2, 1, 0, 2, 0, 2, 0, 2, 0, 1, 0, 2, 0, 1, 2, 0, 2, 1, 0, 1, 0, 2, 0, 2, 1, 0, 2, 1, 2, 0]
    optical = calculate_optical_data(value="67890", type=AMOUNT)
    print "-" * 70
    print "Amo D: %s" % demo_data_amount
    print "Amo O: %s " % optical
    _create_image(optical, outfile="amount.gif")

