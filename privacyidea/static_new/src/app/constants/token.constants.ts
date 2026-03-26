/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

// TOTP Token
export const TOTP_HASHLIB = "totp.hashlib";
export const TOTP_OTP_LENGTH = "totp.otplen";
export const TOTP_TIME_STEP = "totp.timeStep";
export const TOTP_TIME_WINDOW = "totp.timeWindow";
export const TOTP_TIME_SHIFT = "totp.timeShift";

// HOTP Token
export const HOTP_HASHLIB = "hotp.hashlib";
export const HOTP_OTP_LENGTH = "hotp.otplen";

// Daypassword Token
export const DAYPASSWORD_HASHLIB = "daypassword.hashlib";
export const DAYPASSWORD_OTP_LENGTH = "daypassword.otplen";
export const DAYPASSWORD_TIME_STEP = "daypassword.timeStep";

// SMS Token
export const SMS_GATEWAY = "sms.identifier";
export const SMS_PROVIDER_TIMEOUT = "sms.providerTimeout";

// Email Token
export const EMAIL_SMTP_SERVER_KEY = "email.identifier";
export const EMAIL_VALIDITY_TIME_KEY = "email.validtime";

// Yubico Token
export const YUBICO_ID = "yubico.id";
export const YUBICO_SECRET = "yubico.secret";
export const YUBICO_URL = "yubico.url";

// Radius Token
export const RADIUS_SERVER = "radius.identifier";

// TiQR Token
export const TIQR_REG_SERVER = "tiqr.regServer";
export const TIQR_AUTH_SERVER = "tiqr.authServer";
export const TIQR_SERVICE_DISPLAYNAME = "tiqr.serviceDisplayname";
export const TIQR_SERVICE_IDENTIFIER = "tiqr.serviceIdentifier";
export const TIQR_LOGO_URL = "tiqr.logoUrl";
export const TIQR_INFO_URL = "tiqr.infoUrl";
export const TIQR_OCRASUITE = "tiqr.ocrasuite";

// Remote Token
export const REMOTE_SERVER = "remote.server";
export const REMOTE_VERIFY_SSL = "remote.verify_ssl_certificate";

// WebAuthn Token
export const WEBAUTHN_TRUST_ANCHOR_DIR = "webauthn.trust_anchor_dir";

// Questionnaire Token
export const QUESTION_NUMBER_OF_ANSWERS = "question.num_answers";
export const QUESTION_CONFIG_PREFIX = "question.question.";
