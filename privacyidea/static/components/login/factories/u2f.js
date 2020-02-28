/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-10-01 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

angular.module("privacyideaAuth")
    .factory("U2fFactory", ['inform', '$http', 'authUrl', 'gettextCatalog',
        function (inform, $http, authUrl, gettextCatalog) {
            var u2fErrors = [gettextCatalog.getString("OK"),
                gettextCatalog.getString("Other Error"),
                gettextCatalog.getString("Bad U2F Request"),
                gettextCatalog.getString("Client Configuration is not supported."),
                gettextCatalog.getString("The client device can not be used for this type of" +
                    " request."),
                gettextCatalog.getString("Timeout while waiting for signing response.")];

            return {
                register_request: function (registerRequest, callback) {

                    // set variables for U2F API v1.1
                    var appId = registerRequest.appId;
                    var registerRequests = [{
                      version : registerRequest.version,
                      challenge : registerRequest.challenge,
                      attestation : "direct"
                    }];
                    var registeredKeys = [];

                    u2f.register(appId, registerRequests, registeredKeys, function (result) {
                        //debug: console.log(result);
                        if (result.errorCode > 0) {
                            inform.add(u2fErrors[result.errorCode] + " / " + result.errorMessage,
                                {type: "danger", ttl: 10000});
                        } else {
                            // Send the necessary data to privacyIDEA
                            var params = {
                                type: "u2f",
                                regdata: result.registrationData,
                                clientdata: result.clientData
                            };
                            callback(params);
                        }
                    });
                },
                sign_request: function (data, signRequests, username, transactionid,
                                        login_callback) {

                    // set variables for U2F API v1.1
                    var appId = signRequests[0].appId;
                    var challenge = signRequests[0].challenge;
                    var registeredKeys = [];
                    for (var i = 0; i < signRequests.length; i++) {
                        var signRequest = signRequests[i];
                        registeredKeys.push({
                            version: signRequest.version,
                            keyHandle: signRequest.keyHandle
                        });
                    }

                    u2f.sign(appId, challenge, registeredKeys, function (result) {
                        inform.clear();
                        if (result.errorCode > 0) {
                            //debug: console.log("U2F error.");
                            //debug: console.log(result);
                            inform.add(u2fErrors[result.errorCode] + " / " + result.errorMessage,
                                {
                                    type: "danger",
                                    ttl: 10000
                                });
                        } else {
                            //debug: console.log("Got response from U2F device.");
                            $http.post(authUrl, {
                                username: username,
                                password: "",
                                signaturedata: result.signatureData,
                                clientdata: result.clientData,
                                transaction_id: transactionid
                            }, {
                                withCredentials: true
                            }).then(function (response) {
                                login_callback(response.data);
                            }, function (error) {
                                //debug console.log("U2F error:");
                                //debug console.log(error);
                                inform.add(gettextCatalog.getString("Error in U2F response."),
                                    {type: "danger", ttl: 10000});
                            });
                        }
                    });
                }
            };
        }]);

