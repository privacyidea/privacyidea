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

import { TokenApiPayloadMapper, TokenEnrollmentData } from "./_token-api-payload.mapper";
import { HotpApiPayloadMapper } from "./hotp-token-api-payload.mapper";
import { TotpApiPayloadMapper } from "./totp-token-api-payload.mapper";
import { SpassApiPayloadMapper } from "./spass-token-api-payload.mapper";
import { MotpApiPayloadMapper } from "./motp-token-api-payload.mapper";
import { SshkeyApiPayloadMapper } from "./sshkey-token-api-payload.mapper";
import { YubikeyApiPayloadMapper } from "./yubikey-token-api-payload.mapper";
import { RemoteApiPayloadMapper } from "./remote-token-api-payload.mapper";
import { YubicoApiPayloadMapper } from "./yubico-token-api-payload.mapper";
import { RadiusApiPayloadMapper } from "./radius-token-api-payload.mapper";
import { SmsApiPayloadMapper } from "./sms-token-api-payload.mapper";
import { FourEyesApiPayloadMapper } from "./4eyes-token-api-payload.mapper";
import { ApplspecApiPayloadMapper } from "./applspec-token-api-payload.mapper";
import { CertificateApiPayloadMapper } from "./certificate-token-api-payload.mapper";
import { DaypasswordApiPayloadMapper } from "./daypassword-token-api-payload.mapper";
import { EmailApiPayloadMapper } from "./email-token-api-payload.mapper";
import { IndexedSecretApiPayloadMapper } from "./indexedsecret-token-api-payload.mapper";
import { PaperApiPayloadMapper } from "./paper-token-api-payload.mapper";
import { PushApiPayloadMapper } from "./push-token-api-payload.mapper";
import { QuestionApiPayloadMapper } from "./question-token-api-payload.mapper";
import { RegistrationApiPayloadMapper } from "./registration-token-api-payload.mapper";
import { TanApiPayloadMapper } from "./tan-token-api-payload.mapper";
import { TiqrApiPayloadMapper } from "./tiqr-token-api-payload.mapper";
import { U2fApiPayloadMapper } from "./u2f-token-api-payload.mapper";
import { VascoApiPayloadMapper } from "./vasco-token-api-payload.mapper";
import { WebAuthnApiPayloadMapper } from "./webauthn-token-api-payload.mapper";
import { PasskeyApiPayloadMapper } from "./passkey-token-api-payload.mapper";
import type { TokenTypeKey } from "../../services/token/token.service";

// Registry mapping token type strings to mapper instances
export const tokenApiPayloadMapperRegistry: Partial<Record<TokenTypeKey, TokenApiPayloadMapper<TokenEnrollmentData>>> = {
  hotp: new HotpApiPayloadMapper(),
  totp: new TotpApiPayloadMapper(),
  spass: new SpassApiPayloadMapper(),
  motp: new MotpApiPayloadMapper(),
  sshkey: new SshkeyApiPayloadMapper(),
  yubikey: new YubikeyApiPayloadMapper(),
  remote: new RemoteApiPayloadMapper(),
  yubico: new YubicoApiPayloadMapper(),
  radius: new RadiusApiPayloadMapper(),
  sms: new SmsApiPayloadMapper(),
  "4eyes": new FourEyesApiPayloadMapper(),
  applspec: new ApplspecApiPayloadMapper(),
  certificate: new CertificateApiPayloadMapper(),
  daypassword: new DaypasswordApiPayloadMapper(),
  email: new EmailApiPayloadMapper(),
  indexedsecret: new IndexedSecretApiPayloadMapper(),
  paper: new PaperApiPayloadMapper(),
  push: new PushApiPayloadMapper(),
  question: new QuestionApiPayloadMapper(),
  registration: new RegistrationApiPayloadMapper(),
  tan: new TanApiPayloadMapper(),
  tiqr: new TiqrApiPayloadMapper(),
  u2f: new U2fApiPayloadMapper(),
  vasco: new VascoApiPayloadMapper(),
  webauthn: new WebAuthnApiPayloadMapper(),
  passkey: new PasskeyApiPayloadMapper(),
};

// Function to retrieve the correct mapper for a given token type
export function getTokenApiPayloadMapper(tokenType: TokenTypeKey): TokenApiPayloadMapper<TokenEnrollmentData> | undefined {
  return tokenApiPayloadMapperRegistry[tokenType];
}
