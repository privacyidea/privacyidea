/**
 * https://www.privacyidea.org
 * (C) Cornelius Kölbel, cornelius@privacyidea.org
 *
 * 2020-02-13 Jean-Pierre Höhmann, <jean-pierre.hoehmann@netknights.it>
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
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

angular
    .module("privacyideaAuth")
    .factory(
        "webAuthnToken",
        [
            'inform',
            '$http',
            'authUrl',
            'gettextCatalog',
            'domExceptionErrorMessage',
            function webAuthnTokenFactory(
                inform,
                $http,
                authUrl,
                gettextCatalog,
                domExceptionErrorMessage
            ) {
                return {
                    register_request: function(registerRequest, callback) {
                        if (!pi_webauthn) {
                            inform.add(
                                gettextCatalog.getString(
                                    "WebAuthn is not supported by this browser, or in this context."
                                ),
                                {
                                    type: "danger",
                                    ttl: 10000
                                }
                            );
                            return;
                        }

                        pi_webauthn
                            .register(registerRequest)
                            .then(callback)
                            .catch(function(e) {
                                inform.add(
                                    domExceptionErrorMessage[e.name] + " / " + e.message,
                                    {
                                        type: "danger",
                                        ttl: 10000
                                    }
                                );
                            });
                    },
                    sign_request: function(data, signRequests, username, transactionid, login_callback) {
                        if (!pi_webauthn) {
                            inform.add(
                                gettextCatalog.getString(
                                    "WebAuthn is not supported by this browser, or in this context."
                                ),
                                {
                                    type: "danger",
                                    ttl: 10000
                                }
                            );
                            return;
                        }

                        pi_webauthn
                            .sign({
                                challenge: signRequests[0].challenge,
                                allowCredentials: signRequests
                                    .map(function(signRequest) { return signRequest.allowCredentials; })
                                    .reduce(function(acc, val) { return acc.concat(val); }, []),
                                rpId: signRequests[0].rpId,
                                userVerification: signRequests[0].userVerification,
                                timeout: signRequests[0].timeout
                            })
                            .then(function (signResponse) {
                                inform.clear();
                                signResponse.username = username;
                                signResponse.password = "";
                                signResponse.transaction_id = transactionid;
                                return $http.post(authUrl, signResponse, {withCredentials: true})
                            })
                            .then(function(response) { return response.data; })
                            .then(login_callback)
                            .catch(function(e) {
                                inform.add(
                                    e instanceof DOMException
                                        ? domExceptionErrorMessage[e.name] + " / " + e.message
                                        : gettextCatalog.getString("Error in WebAuthn response."),
                                    {
                                        type: "danger",
                                        ttl: 10000
                                    }
                                );
                            });
                    },
                };
            }
        ]
    );
