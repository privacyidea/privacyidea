#!/bin/bash
# privacyidea-fetchssh.bash

# This script queries the json interface of a privacyid3a server to retrieve
# the public ssh key for a specific host (hostname).
# With this script you can test the 'privacyidea-authorizedkeys' function of 
# your privacyid3a server from a remote host.
#
# Some small modifications to this script (paramaters for the input values and
# some plausibility checks should be enought to use it as a replacement for
# 'privacyidea-authorizedkeys' and to have less dependencies.
# 
# If debug is set to 0 the script only echoes the public key.
# If debug is set to 1 you will see a lot of information.
#
# History
# v0.1	03/31/2015	Peter Murr	mailinglists [at] pcfreak [dot] de


#input parameters
server='localhost'
username='admin'
password='test'
hostname=`hostname`
debug=0 # 0 or 1
insecure=""
#insecure="-k"

# some checks for dependencies
command -v jq >/dev/null 2>&1 || { echo >&2 "script requires jq but it is not installed.  Aborting."; exit 2; }
command -v sed >/dev/null 2>&1 || { echo >&2 "script requires sed but it is not installed.  Aborting."; exit 2; }
command -v sed >/dev/null 2>&1 || { echo >&2 "script requires curl but it is not installed.  Aborting."; exit 2; }
command -v sed >/dev/null 2>&1 || { echo >&2 "script requires tr but it is not installed.  Aborting."; exit 2; }

# other variables
baseurl="https://$server"
application='ssh'
headersalways1='Content-type: application/json'
headersalways2='Accept: application/json'
cpar="-s $insecure"  # add -v to get verbose output if you search for bugs!

# retrieve authentication token (we need this for all further requests
# see http://privacyidea.readthedocs.org/en/latest/modules/api/auth.html
# this is a POST request with data
json=$(curl $cpar -H "$headersalways1" -H "$headersalways2" -d '{ "username":"'$username'", "password":"'$password'" }' $baseurl/auth)
jstatus=$(echo "$json"|jq .result.status)
if [[ "$jstatus" != "true" ]]; then # if request failed .result.status=false
  # TODO: If the SSL cert fails, we also run into this tree
  echo "Could not get a valid token with the provided credentials"
  exit 1
else
  token=$(echo "$json"|jq .result.value.token|sed 's/"//g') # get token from json and remove double quotes
fi

# List all machines that can be found in the machine resolvers.
json=$(curl $cpar -L -G -H "$headersalways1" -H "$headersalways2" -H "Authorization: $token" https://$server/machine 2>/dev/null)
jstatus=$(echo "$json"|jq .result.status)
if [[ "$jstatus" != "true" ]]; then
  echo "Could not retrieve any machine resolvers!"
else
 if [[ "$debug" == "1" ]]; then
   hostnames=$(echo $json|jq .result.value[].hostname[]|sed 's/"//g'|tr "\n" " "|sed "s/\(${hostname}\)/\[*\]\1/g") # mark the host in output
   echo ""
   echo "available machine resolvers: $hostnames"
   echo ""
 fi
fi

# Fetch the authentication items for a given application 'ssh' and the given client machine [hostname].
# this is a simple GET request with the hostname as parameter
json=$(curl $cpar -G -H "Authorization: $token" -d "hostname=$hostname" $baseurl/machine/authitem/$application)
jstatus=$(echo "$json"|jq .result.status)
if [[ "$jstatus" == "true" ]]; then
   resultusername=$(echo "$json"|jq .result.value.ssh[0].username|sed 's/"//g') # remove double quotes also
   resultuser=$(echo "$json"|jq .result.value.ssh[0].user|sed 's/"//g') # remove double quotes also
   resultsshkey=$(echo "$json"|jq .result.value.ssh[0].sshkey|sed 's/"//g') # remove double quotes also
 if [[ "$debug" == "1" ]];then 
   echo "hostname: $hostname"
   echo "username: $resultusername"
   echo "user    : $resultuser"
   echo "sshkey  : $resultsshkey"
 else
   echo "$resultsshkey"
 fi
else
 echo "no successful query!"
fi
