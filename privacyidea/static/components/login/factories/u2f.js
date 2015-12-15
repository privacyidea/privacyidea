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
                    u2f.register([registerRequest], [], function (result) {
                        console.log(result);
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
                sign_request: function (data, username, transactionid,
                                        login_callback) {
                    var signRequests = [data.detail.attributes.u2fSignRequest];
                    u2f.sign(signRequests, function (result) {
                        inform.clear();
                        if (result.errorCode > 0) {
                            console.log("U2F error.");
                            console.log(result);
                            inform.add(u2fErrors[result.errorCode] + " / " + result.errorMessage,
                                {
                                    type: "danger",
                                    ttl: 10000
                                });
                        } else {
                            console.log("Got response from U2F device.");
                            $http.post(authUrl, {
                                username: username,
                                password: "",
                                signaturedata: result.signatureData,
                                clientdata: result.clientData,
                                transaction_id: transactionid
                            }, {
                                withCredentials: true
                            }).success(function (data) {
                                login_callback(data);
                            }).error(function (data) {
                                inform.add(gettextCatalog.getString("Error in U2F response."),
                                    {type: "danger", ttl: 10000});
                            });
                        }
                    });
                }
            };
        }]);

