/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
export const tokenTypes = [
  {
    key: "hotp",
    text: "The HOTP token is an event based token. With a smartphone app like the privacyIDEA Authenticator" +
      " you can turn your smartphone into an authentication device."
  },
  {
    key: "totp",
    text: "The TOTP token is a time based token. With a smartphone app like the privacyIDEA Authenticator" +
      " you can turn your smartphone into an authentication device."
  },
  {
    key: "spass",
    text: "The Simple Pass Token does not take additional arguments. You only need to specify an OTP PIN.\n"
  },
  {
    key: "motp",
    text: "The mOTP token is a time based OTP token for mobile devices. You can have the server generate the secret" +
      " and scan the QR code."
  },
  {
    key: "sshkey",
    text: "The SSH Key Token stores the public SSH Key in the server. This can be used to authenticate to a secure shell."
  },
  {
    key: "yubikey",
    text: "The Yubikey Token is an USB device that emits an event based One Time Password. You can initialize the" +
      " Yubikey using the YubiKey personalization tools. The secret hex key and the final OTP length are needed here." +
      " For tokens compatible with the Yubico cloud service the OTP length must be 44 (12 characters UID and 32 " +
      "characters OTP). When programming the token for the Yubico cloud service, the Public Identity Length must be 6" +
      " bytes, which will give you a UID with 12 characters. The current OTP length of a programmed YubiKey can " +
      "automatically be determined by inserting it in the test field."
  },
  {
    key: "remote",
    text: "The remote token forwards the authentication request to another privacyIDEA server."
  },
  {
    key: "yubico",
    text: "The Yubico Cloud mode forwards the authentication request to the YubiCloud. The Yubikey needs to be " +
      "registered with the YubiCloud."
  },
  {
    key: "radius",
    text: "The RADIUS token forwards the authentication request to another RADIUS server."
  },
  {
    key: "sms",
    text: "The SMS Token sends an OTP value to the mobile phone of the user."
  },
  {
    key: "4eyes",
    text: "The 4 Eyes token will only authenticate if two or more users use their token in succession. You can" +
      " define how many tokens are required for a successful authentication."
  },
  {
    key: "applspec",
    text: "The Application Specific Password token is a static password, that is bound to certain services."
  },
  {
    key: "certificate",
    text: "The Certificate Token lets you enroll an x509 certificate with the specified Certificate Authority."
  },
  {
    key: "daypassword",
    text: "The DayPassword token is a time based password token with a larger time window. OTP values of this" +
      " token can be reused by default."
  },
  {
    key: "email",
    text: "The Email Token sends the OTP value to the users email address."
  },
  {
    key: "indexedsecret",
    text: "The indexed secret Token is based on a shared secret between privacyIDEA and the user. During " +
      "authentication, the user is asked for characters at random positions of this known secret."
  },
  {
    key: "paper",
    text: "The Paper token will let you print a list of OTP values. In contrast to the TAN token, the OTP values" +
      " have to be used in order."
  },
  {
    key: "push",
    text: "The PUSH token works with the privacyIDEA Authenticator App. It will send an authentication request to" +
      " the app, which can be accepted by just tapping a button. Optionally, it can require users to use the" +
      " configured unlock mechanism (PIN/Biometric) on their smartphone to accept." +
      "The smartphone needs to be able to reach privacyIDEA for this token to work."
  },
  {
    key: "question",
    text: "The Questionnaire token will let you define answers to questions. When authenticating with this type of " +
      "token, you will be asked a random question and then need to provide the previously defined answer."
  },
  {
    key: "registration",
    text: "The registration token is a code, that the user can use to authenticate once. Then the token is deleted" +
      " automatically. This can be useful for setting up users."
  },
  {
    key: "tan",
    text: "The TAN token will let you print a list of OTP values. In contrast to the Paper token, the OTP values can" +
      " be used in an arbitrary order."
  },
  {
    key: "tiqr",
    text: "The TiQR token is a Smartphone App token, which allows easy authentication by just scanning a QR Code " +
      "during the authentication process."
  },
  {
    key: "u2f",
    text: "The U2F token is a token defined by the Fido Alliance. It is the predecessor to WebAuthn/Passkey, " +
      "has been superseded by them, and therefore should not be used any more."
  },
  {
    key: "vasco",
    text: "The VASCO token is a proprietary OTP token. You can paste the VASCO token blob in hex format."
  },
  {
    key: "webauthn",
    text: "A WebAuthn token is a phishing-resistant credential that uses public-key cryptography to prove your " +
      "identity without sharing a secret. The WebAuthn token stores the encrypted key on the server to allow" +
      " unlimited registrations."
  },
  {
    key: "passkey",
    text: "A passkey is a phishing-resistant credential that uses public-key cryptography to prove your identity " +
      "without sharing a secret. The private key is stored securely on your authenticator (like a phone or " +
      "hardware token) and is unlocked for each sign-in using your device's PIN, fingerprint, or face scan."
  }
];