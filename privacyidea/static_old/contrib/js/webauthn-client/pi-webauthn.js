/*
 * 2020-02-11 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
 *
 * License:     AGPLv3
 * Contact:     https://www.privacyidea.org
 *
 * Copyright (C) 2020 NetKnights GmbH
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
 */

/**
 * Namespace for the WebAuthn api.
 */
var pi_webauthn = navigator.credentials ? window.pi_webauthn || {} : null;

/**
 * WebAuthn wrapper functions for privacyIDEA.
 */
(function(credentials) {
    'use strict';

    // Do not proceed if webAuthn is unsupported in this client.
    if (!this) { return; }

    /**
     * Convert a UTF-8 encoded base64 character to a base64 digit.
     *
     * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
     *
     * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
     *
     * Author: madmurphy
     *
     * @param {number} nChr - A UTF-8 encoded base64 character.
     *
     * @returns {number} - The base64 digit.
     */
    var b64ToUint6 = function(nChr) {
        return nChr > 64 && nChr < 91
            ? nChr - 65
            : nChr > 96 && nChr < 123
                ? nChr - 71
                : nChr > 47 && nChr < 58
                    ? nChr + 4
                    : nChr === 43
                        ? 62
                        : nChr === 47
                            ? 63
                            : 0;
    };

    /**
     * Convert a base64 digit, to a UTF-8 encoded base64 character.
     *
     * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
     *
     * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
     *
     * Author: madmurphy
     *
     * @param {number} nUint6 - A base64 digit.
     *
     * @returns {number} - The UTF-8 encoded base64 character.
     */
    var uint6ToB64 = function(nUint6) {
        return nUint6 < 26 ?
                nUint6 + 65
            : nUint6 < 52 ?
                nUint6 + 71
            : nUint6 < 62 ?
                nUint6 - 4
            : nUint6 === 62 ?
                43
            : nUint6 === 63 ?
                47
            :
                65;
    };

    /**
     * Decode base64 into UTF-8.
     *
     * This will take a base64 encoded string and decode it to UTF-8,
     * optionally NUL-padding it to make its length a multiple of a given
     * block size.
     *
     * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
     *
     * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
     *
     * Author: madmurphy
     *
     * @param {string} sBase64 - Base64 to decode.
     * @param {number} [nBlockSize=1] - The block-size for the output.
     *
     * @returns {Uint8Array} - The decoded string.
     */
    var base64DecToArr = function(sBase64, nBlockSize) {
        var sB64Enc = sBase64.replace(/[^A-Za-z0-9+\/]/g, "");
        var nInLen = sB64Enc.length;
        var nOutLen = nBlockSize ?
                Math.ceil((nInLen * 3 + 1 >>> 2) / nBlockSize) * nBlockSize
            :
                nInLen * 3 + 1 >>> 2;
        var aBytes = new Uint8Array(nOutLen);

        for (var nMod3, nMod4, nUint24 = 0, nOutIdx = 0, nInIdx = 0; nInIdx < nInLen; nInIdx++) {
            nMod4 = nInIdx & 3;
            nUint24 |= b64ToUint6(sB64Enc.charCodeAt(nInIdx)) << 18 - 6 * nMod4;
            if (nMod4 === 3 || nInLen - nInIdx === 1) {
                for (nMod3 = 0; nMod3 < 3 && nOutIdx < nOutLen; nMod3++, nOutIdx++) {
                    aBytes[nOutIdx] = nUint24 >>> (16 >>> nMod3 & 24) & 255;
                }
                nUint24 = 0;
            }
        }

        return aBytes;
    };

    /**
     * Encode a binary into base64.
     *
     * This will take a binary ArrayBufferLike and encode it into base64.
     *
     * Adapted from Base64 / binary data / UTF-8 strings utilities (#2)
     *
     * Source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
     *
     * Author: madmurphy
     *
     * @param {ArrayBufferLike} bytes - Bytes to encode.
     *
     * @returns {string} - The encoded base64.
     */
    var base64EncArr = function(bytes) {
        var aBytes = new Uint8Array(bytes)
        var eqLen = (3 - (aBytes.length % 3)) % 3;
        var sB64Enc = "";

        for (var nMod3, nLen = aBytes.length, nUint24 = 0, nIdx = 0; nIdx < nLen; nIdx++) {
            nMod3 = nIdx % 3;

            // Split the output in lines 76-characters long
            if (nIdx > 0 && (nIdx * 4 / 3) % 76 === 0) { sB64Enc += "\r\n"; }

            nUint24 |= aBytes[nIdx] << (16 >>> nMod3 & 24);
            if (nMod3 === 2 || aBytes.length - nIdx === 1) {
                sB64Enc += String.fromCharCode(
                    uint6ToB64(nUint24 >>> 18 & 63),
                    uint6ToB64(nUint24 >>> 12 & 63),
                    uint6ToB64(nUint24 >>> 6 & 63),
                    uint6ToB64(nUint24 & 63));
                nUint24 = 0;
            }
        }

        return eqLen === 0 ?
                sB64Enc
            :
                sB64Enc.substring(0, sB64Enc.length - eqLen) + (eqLen === 1 ? "=" : "==");
    };

    /**
     * Perform web-safe base64 decoding.
     *
     * This will perform web-safe base64 decoding as specified by WebAuthn.
     *
     * @param {string} sBase64 - Base64 to decode.
     *
     * @returns {Uint8Array} - The decoded binary.
     */
    var webAuthnBase64DecToArr = function(sBase64) {
        return base64DecToArr(
            sBase64
                .replace(/-/g, '+')
                .replace(/_/g, '/')
                .padEnd((sBase64.length | 3) + 1, '='))
    };

    /**
     * Perform web-safe base64 encoding.
     *
     * This will perform web-safe base64 encoding as specified by WebAuthn.
     *
     * @param {ArrayBufferLike} bytes - Bytes to encode.
     *
     * @returns {string} - The encoded base64.
     */
    var webAuthnBase64EncArr = function(bytes) {
        return base64EncArr(bytes)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    };

    /**
     * Decode a UTF-8-string.
     *
     * This will accept a UTF-8 string and decode it into the native string
     * representation of the JavaScript engine (read: UTF-16). This function
     * currently implements no sanity checks whatsoever. If the input is not
     * valid UTF-8, the result of this function is not well-defined!
     *
     * @param {Uint8Array} aBytes - A UTF-8 encoded string.
     *
     * @returns {string} The decoded string.
     */
    var utf8ArrToStr = function(aBytes) {
        var sView = "";

        for (var nPart, nLen = aBytes.length, nIdx = 0; nIdx < nLen; nIdx++) {
            nPart = aBytes[nIdx];
            sView += String.fromCharCode(
                nPart > 251 && nPart < 254 && nIdx + 5 < nLen ?
                        (nPart - 252) * 1073741824 /* << 30 */
                            + (aBytes[++nIdx] - 128 << 24)
                            + (aBytes[++nIdx] - 128 << 18)
                            + (aBytes[++nIdx] - 128 << 12)
                            + (aBytes[++nIdx] - 128 << 6)
                            + aBytes[++nIdx] - 128
                    : nPart > 247 && nPart < 252 && nIdx + 4 < nLen ?
                        (nPart - 248 << 24)
                            + (aBytes[++nIdx] - 128 << 18)
                            + (aBytes[++nIdx] - 128 << 12)
                            + (aBytes[++nIdx] - 128 << 6)
                            + aBytes[++nIdx] - 128
                    : nPart > 239 && nPart < 248 && nIdx + 3 < nLen ?
                        (nPart - 240 << 18)
                            + (aBytes[++nIdx] - 128 << 12)
                            + (aBytes[++nIdx] - 128 << 6)
                            + aBytes[++nIdx] - 128
                    : nPart > 223 && nPart < 240 && nIdx + 2 < nLen ?
                        (nPart - 224 << 12)
                            + (aBytes[++nIdx] - 128 << 6)
                            + aBytes[++nIdx] - 128
                    : nPart > 191 && nPart < 224 && nIdx + 1 < nLen ?
                        (nPart - 192 << 6)
                            + aBytes[++nIdx] - 128
                    :
                        nPart
            );
        }

        return sView;
    };

    /**
     * Encode a string to UTF-8.
     *
     * This will accept a string in the native representation of the JavaScript
     * engine (read: UTF-16), and encode it as UTF-8.
     *
     * @param {string} sDOMStr - A string to encode.
     *
     * @returns {Uint8Array} - The encoded string.
     */
    var strToUtf8Arr = function(sDOMStr) {
        var aBytes;
        var nChr;
        var nStrLen = sDOMStr.length;
        var nArrLen = 0;

        /*
         * Determine the byte-length of the string when encoded as UTF-8.
         */

        for (var nMapIdx = 0; nMapIdx < nStrLen; nMapIdx++) {
            nChr = sDOMStr.charCodeAt(nMapIdx);
            nArrLen += nChr < 0x80 ?
                    1
                : nChr < 0x800 ?
                    2
                : nChr < 0x10000 ?
                    3
                : nChr < 0x200000 ?
                    4
                : nChr < 0x4000000 ?
                    5
                :
                    6;
        }

        aBytes = new Uint8Array(nArrLen);

        /*
         * Perform the encoding.
         */

        for (var nIdx = 0, nChrIdx = 0; nIdx < nArrLen; nChrIdx++) {
            nChr = sDOMStr.charCodeAt(nChrIdx);
            if (nChr < 128) {
                /* one byte */
                aBytes[nIdx++] = nChr;
            } else if (nChr < 0x800) {
                /* two bytes */
                aBytes[nIdx++] = 192 + (nChr >>> 6);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else if (nChr < 0x10000) {
                /* three bytes */
                aBytes[nIdx++] = 224 + (nChr >>> 12);
                aBytes[nIdx++] = 128 + (nChr >>> 6 & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else if (nChr < 0x200000) {
                /* four bytes */
                aBytes[nIdx++] = 240 + (nChr >>> 18);
                aBytes[nIdx++] = 128 + (nChr >>> 12 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 6 & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else if (nChr < 0x4000000) {
                /* five bytes */
                aBytes[nIdx++] = 248 + (nChr >>> 24);
                aBytes[nIdx++] = 128 + (nChr >>> 18 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 12 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 6 & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
            } else /* if (nChr <= 0x7fffffff) */ {
                /* six bytes */
                aBytes[nIdx++] = 252 + (nChr >>> 30);
                aBytes[nIdx++] = 128 + (nChr >>> 24 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 18 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 12 & 63);
                aBytes[nIdx++] = 128 + (nChr >>> 6 & 63);
                aBytes[nIdx++] = 128 + (nChr & 63);
            }
        }

        return aBytes;
    };

    /**
     * Create a new credential from a WebAuthnRegisterRequest.
     *
     * This will accept a WebAuthnRegisterRequest, as returned by a call to
     * the /token/init endpoint. It will format the data as necessary and pass
     * it to navigator.credentials.create(), the result of the call will be
     * processed and a WebAuthnRegisterResponse, ready to be passed on to
     * privacyIDEA, will be returned.
     *
     * @param {WebAuthnRegisterRequest} webAuthnRegisterRequest - The request as provided by privacyIDEA.
     *
     * @returns {Promise<WebAuthnRegisterResponse>} - Information to pass to /token/init.
     *
     * @typedef WebAuthnRegisterRequest
     * @type {object}
     * @property {string} transaction_id - The transaction id from privacyIDEA.
     * @property {string} message - Unused.
     * @property {string} serialNumber - The serial number of the new token being enrolled.
     * @property {string} name - The login name of the user the token is being enrolled for.
     * @property {string} displayName - The full name of the user the token is being enrolled for.
     * @property {string} nonce - The challenge to use when creating the token.
     * @property {PublicKeyCredentialRpEntity} relyingParty - The relyingParty to use for the credential.
     * @property {PublicKeyCredentialParameters} pubKeyCredAlgorithms - The preferred algorithm for credential creation.
     * @property {AuthenticatorSelectionCriteria} [authenticatorSelection] - Selection criteria for authenticators.
     * @property {number} [timeout=60000] - Timeout in milliseconds.
     * @property {AttestationConveyancePreference} [attestation="direct"] - Option to discourage or require attestation.
     * @property {sequence<AAGUID>} [authenticatorSelectionList] - A whitelist of authenticators to allow.
     * @property {string} [description] - A description for the token being created.
     *
     * @typedef WebAuthnRegisterResponse
     * @type {object}
     * @property {'webauthn'} type - The token type of the token being enrolled.
     * @property {string} transaction_id - The transaction_id that was passed in.
     * @property {string} clientdata - The clientDataJSON, encoded in base64.
     * @property {string} regdata - The attestationObject, encoded in base64.
     * @property {string} registrationclientextensions - The registrationClientExtensions, encoded in JSON.
     * @property {string} [description] - The description
     */
    this.register = function(webAuthnRegisterRequest) {
        var publicKeyCredentialCreationOptions = {
            challenge: webAuthnBase64DecToArr(webAuthnRegisterRequest.nonce),
            rp: webAuthnRegisterRequest.relyingParty,
            user: {
                id: strToUtf8Arr(webAuthnRegisterRequest.serialNumber),
                name: webAuthnRegisterRequest.name,
                displayName: webAuthnRegisterRequest.displayName
            },
            pubKeyCredParams: webAuthnRegisterRequest.pubKeyCredAlgorithms,
            timeout: webAuthnRegisterRequest.timeout || 60000,
            attestation: webAuthnRegisterRequest.attestation || "direct",
            extensions: {}
        };
        if (webAuthnRegisterRequest.authenticatorSelection) {
            publicKeyCredentialCreationOptions.authenticatorSelection
                = webAuthnRegisterRequest.authenticatorSelection;
        }
        if (webAuthnRegisterRequest.authenticatorSelectionList) {
            publicKeyCredentialCreationOptions.extensions.authnSel
                = webAuthnRegisterRequest.authenticatorSelectionList
        }
        if (webAuthnRegisterRequest.excludeCredentials) {
            publicKeyCredentialCreationOptions.excludeCredentials
                = webAuthnRegisterRequest.excludeCredentials.map(function (x) {
                    return {
                        id: webAuthnBase64DecToArr(x.id),
                        transports: x.transports,
                        type: x.type
                    }
                });
        }


        return navigator
            .credentials
            .create({publicKey: publicKeyCredentialCreationOptions})
            .then(function(credential) {
                if (!credential) { return Promise.reject(); }

                var webAuthnRegisterResponse = {
                    type: 'webauthn',
                    transaction_id: webAuthnRegisterRequest.transaction_id,
                    clientdata: webAuthnBase64EncArr(credential.response.clientDataJSON),
                    regdata: webAuthnBase64EncArr(credential.response.attestationObject),
                };

                var  clientExtensionResults = credential.getClientExtensionResults();
                if (clientExtensionResults && Object.keys(clientExtensionResults).length) {
                    webAuthnRegisterResponse.registrationclientextensions = webAuthnBase64EncArr(
                        strToUtf8Arr(JSON.stringify(clientExtensionResults)));
                }

                return Promise.resolve(webAuthnRegisterResponse);
            });
    };

    /**
     * Create a signature from a WebAuthnSignRequest.
     *
     * This will accept a WebAuthnSignRequest, as returned by a call to the
     * /validate/check, or the /validate/triggerchallenge endpoint. It will
     * format the data as necessary and pass it to navigator.credentials.get(),
     * the result of the call will be processed and a WebAuthnSignResponse will
     * be returned. The fields from the WebAuthnSignResponse need to be passed
     * back to the /validate/check endpoint, along with the `user`, and
     * `transaction_id` associated with the signing request.
     *
     * @param {WebAuthnSignRequest} webAuthnSignRequest - The WebAuthnSignRequest as provided by privacyIDEA.
     *
     * @returns {Promise<WebAuthnSignResponse>} - Data for /validate/check minus `user`, `pass`, and `transaction_id`.
     *
     * @typedef WebAuthnSignRequest
     * @type {object}
     * @property {string} challenge - The challenge from privacyIDEA.
     * @property {{id: string, type: PublicKeyCredentialType, transports: AuthenticatorTransport[]}[]} allowCredentials - Creds to try.
     * @property {string} rpId - The relying party id the credential was created with.
     * @property {UserVerificationRequirement} userVerification - Option to discourage, or require user verification.
     * @property {number} [timeout=60000] - Timeout in milliseconds.
     *
     * @typedef WebAuthnSignResponse
     * @type {object}
     * @property {string} credentialid - The id of the credential being used.
     * @property {string} clientdata - The clientDataJSON, encoded in base64.
     * @property {string} signaturedata - The signature, encoded in base64.
     * @property {string} authenticatordata - The authenticatorData, encoded in base64.
     * @property {string} [userhandle] - The userHandle as reported by the authenticator.
     * @property {string} [assertionclientextensions] - The assertionClientExtensions, encoded in JSON.
     */
    this.sign = function (webAuthnSignRequest) {
        var publicKeyCredentialRequestOptions = {
            challenge: webAuthnBase64DecToArr(webAuthnSignRequest.challenge),
            allowCredentials: webAuthnSignRequest.allowCredentials.map(function (x) {
                return {
                    id: webAuthnBase64DecToArr(x.id),
                    type: x.type,
                    transports: x.transports
                }
            }),
            rpId: webAuthnSignRequest.rpId,
            userVerification: webAuthnSignRequest.userVerification,
            timeout: webAuthnSignRequest.timeout || 60000
        };

        return navigator
            .credentials
            .get({publicKey: publicKeyCredentialRequestOptions})
            .then(function (assertion) {
                if (!assertion) { return Promise.reject(); }

                var webAuthnSignResponse = {
                    credentialid: assertion.id,
                    clientdata: webAuthnBase64EncArr(assertion.response.clientDataJSON),
                    signaturedata: webAuthnBase64EncArr(assertion.response.signature),
                    authenticatordata: webAuthnBase64EncArr(assertion.response.authenticatorData)
                };

                if (assertion.response.userHandle) {
                    webAuthnSignResponse.userhandle = utf8ArrToStr(
                        assertion.response.userHandle);
                }
                if (assertion.response.assertionClientExtensions) {
                    webAuthnSignResponse.assertionclientextensions = webAuthnBase64EncArr(
                        strToUtf8Arr(JSON.stringify(assertion.response.assertionClientExtensions)))
                }

                return Promise.resolve(webAuthnSignResponse);
            });
    };
}).bind(pi_webauthn)(navigator.credentials);
