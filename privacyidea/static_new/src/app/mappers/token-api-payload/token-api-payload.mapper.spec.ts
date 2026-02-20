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
import { ApplspecApiPayloadMapper, ApplspecEnrollmentData } from "./applspec-token-api-payload.mapper";
import { CertificateApiPayloadMapper, CertificateEnrollmentData } from "./certificate-token-api-payload.mapper";
import { DaypasswordApiPayloadMapper, DaypasswordEnrollmentData } from "./daypassword-token-api-payload.mapper";
import { EmailApiPayloadMapper, EmailEnrollmentData } from "./email-token-api-payload.mapper";
import { HotpApiPayloadMapper, HotpEnrollmentData } from "./hotp-token-api-payload.mapper";
import { IndexedSecretApiPayloadMapper, IndexedSecretEnrollmentData } from "./indexedsecret-token-api-payload.mapper";
import { MotpApiPayloadMapper, MotpEnrollmentData } from "./motp-token-api-payload.mapper";
import { PaperApiPayloadMapper, PaperEnrollmentData } from "./paper-token-api-payload.mapper";
import {
  PasskeyApiPayloadMapper,
  PasskeyEnrollmentData,
  PasskeyFinalizeApiPayloadMapper,
  PasskeyFinalizeData
} from "./passkey-token-api-payload.mapper";
import { PushApiPayloadMapper, PushEnrollmentData } from "./push-token-api-payload.mapper";
import { QuestionApiPayloadMapper, QuestionEnrollmentData } from "./question-token-api-payload.mapper";
import { RadiusApiPayloadMapper, RadiusEnrollmentData } from "./radius-token-api-payload.mapper";
import { RegistrationApiPayloadMapper, RegistrationEnrollmentData } from "./registration-token-api-payload.mapper";
import { RemoteApiPayloadMapper, RemoteEnrollmentData } from "./remote-token-api-payload.mapper";
import { SmsApiPayloadMapper, SmsEnrollmentData } from "./sms-token-api-payload.mapper";
import { SpassApiPayloadMapper, SpassEnrollmentData } from "./spass-token-api-payload.mapper";
import { SshkeyApiPayloadMapper, SshkeyEnrollmentData } from "./sshkey-token-api-payload.mapper";
import { TanApiPayloadMapper, TanEnrollmentData } from "./tan-token-api-payload.mapper";
import { TiqrApiPayloadMapper, TiqrEnrollmentData } from "./tiqr-token-api-payload.mapper";
import { TotpApiPayloadMapper, TotpEnrollmentData } from "./totp-token-api-payload.mapper";
import { U2fApiPayloadMapper, U2fEnrollmentData } from "./u2f-token-api-payload.mapper";
import { VascoApiPayloadMapper, VascoEnrollmentData } from "./vasco-token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnFinalizeData
} from "./webauthn-token-api-payload.mapper";
import { FourEyesApiPayloadMapper, FourEyesEnrollmentData } from "./4eyes-token-api-payload.mapper";
import { YubikeyApiPayloadMapper, YubikeyEnrollmentData } from "./yubikey-token-api-payload.mapper";
import { YubicoApiPayloadMapper, YubicoEnrollmentData } from "./yubico-token-api-payload.mapper";

const common = {
  description: "desc",
  containerSerial: "CONT-1",
  validityPeriodStart: "2025-01-01",
  validityPeriodEnd: "2025-12-31",
  user: "alice",
  realm: "realm1",
  onlyAddToRealm: false,
  pin: "1234",
  serial: null as string | null
};

describe("FourEyesApiPayloadMapper", () => {
  const mapper = new FourEyesApiPayloadMapper();
  const base = (): FourEyesEnrollmentData => ({
    ...common,
    type: "4eyes",
    separator: ",",
    requiredTokenOfRealms: [
      { realm: "rA", tokens: 2 },
      { realm: "rB", tokens: 1 }
    ]
  });

  it("maps full payload", () => {
    const payload = mapper.toApiPayload(base());
    expect(payload).toEqual({
      type: "4eyes",
      description: "desc",
      container_serial: "CONT-1",
      validity_period_start: "2025-01-01",
      validity_period_end: "2025-12-31",
      user: "alice",
      realm: "realm1",
      pin: "1234",
      separator: ",",
      "4eyes": { rA: { count: 2, selected: true }, rB: { count: 1, selected: true } }
    });
  });

  it("respects onlyAddToRealm", () => {
    const data = base();
    data.onlyAddToRealm = true;
    const payload = mapper.toApiPayload(data);
    expect(payload.user).toBeNull();
    expect(payload.realm).toBe("realm1");
  });

  it("nulls realm if user empty", () => {
    const data = base();
    data.user = "";
    const payload = mapper.toApiPayload(data);
    expect(payload.realm).toBeUndefined();
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to FourEyesEnrollmentData", () => {
    const details = {
      tokentype: "4eyes",
      description: "desc",
      container_serial: "CONT-1",
      info: { separator: ";", "4eyes": "realmA:2,realmB:3" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("4eyes");
    expect(result.serial).toBe("S1");
    expect(result.separator).toBe(";");
    expect(result.requiredTokenOfRealms).toEqual([
      { realm: "realmA", tokens: 2 },
      { realm: "realmB", tokens: 3 }
    ]);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to FourEyesEnrollmentData defaults", () => {
    const details = {
      tokentype: "4eyes",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("4eyes");
    expect(result.separator).toBe("");
    expect(result.requiredTokenOfRealms).toEqual([]);
  });
});

describe("ApplspecApiPayloadMapper", () => {
  const mapper = new ApplspecApiPayloadMapper();
  const base = (): ApplspecEnrollmentData => ({
    ...common,
    type: "applspec",
    generateOnServer: false,
    otpKey: "KEY",
    serviceId: "svc-1"
  });

  it("maps with client-provided key", () => {
    const p = mapper.toApiPayload(base());
    expect(p).toEqual({
      type: "applspec",
      description: "desc",
      container_serial: "CONT-1",
      validity_period_start: "2025-01-01",
      validity_period_end: "2025-12-31",
      user: "alice",
      realm: "realm1",
      pin: "1234",
      otpkey: "KEY",
      genkey: 0,
      service_id: "svc-1"
    });
  });

  it("maps generateOnServer", () => {
    const d = base();
    d.generateOnServer = true;
    d.otpKey = "ignored";
    const p = mapper.toApiPayload(d);
    expect(p.otpkey).toBeNull();
    expect(p.genkey).toBe(1);
  });

  it("omits service_id when undefined", () => {
    const d = base();
    d.serviceId = undefined;
    const p = mapper.toApiPayload(d);
    expect("service_id" in p).toBe(false);
  });

  it("respects onlyAddToRealm", () => {
    const d = base();
    d.onlyAddToRealm = true;
    const p = mapper.toApiPayload(d);
    expect(p.user).toBeNull();
    expect(p.realm).toBe("realm1");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to ApplspecEnrollmentData", () => {
    const details = {
      tokentype: "applspec",
      description: "desc",
      container_serial: "CONT-1",
      info: { validity_period_start: "2025-01-01", validity_period_end: "2025-12-31", service_id: "1234" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("applspec");
    expect(result.serial).toBe("S1");
    expect(result.serviceId).toBe("1234");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to ApplspecEnrollmentData defaults", () => {
    const details = {
      tokentype: "applspec",
      description: "desc",
      container_serial: "CONT-1",
      info: { validity_period_start: "2025-01-01", validity_period_end: "2025-12-31" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("applspec");
    expect(result.serial).toBe("S1");
    expect(result.serviceId).toBeUndefined();
  });
});

describe("CertificateApiPayloadMapper", () => {
  const mapper = new CertificateApiPayloadMapper();
  const base = (): CertificateEnrollmentData => ({
    ...common,
    type: "certificate",
    caConnector: "ca1",
    certTemplate: "tplA",
    pem: "PEM"
  });

  it("maps and keeps genkey=1", () => {
    const p = mapper.toApiPayload(base());
    expect(p.genkey).toBe(1);
    expect(p.ca).toBe("ca1");
    expect(p.template).toBe("tplA");
    expect(p.pem).toBe("PEM");
  });

  it("omits optional undefined", () => {
    const d = { ...base(), caConnector: undefined, certTemplate: undefined, pem: undefined };
    const p = mapper.toApiPayload(d);
    expect("ca" in p).toBe(false);
    expect("template" in p).toBe(false);
    expect("pem" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to CertificateEnrollmentData defaults", () => {
    const details = {
      tokentype: "certificate",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("certificate");
    expect(result.serial).toBe("S1");
    expect(result.caConnector).toBeUndefined();
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to CertificateEnrollmentData", () => {
    const details = {
      tokentype: "certificate",
      description: "desc",
      container_serial: "CONT-1",
      info: { CA: "testCA" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("certificate");
    expect(result.serial).toBe("S1");
    expect(result.caConnector).toBe("testCA");
  });
});

describe("DaypasswordApiPayloadMapper", () => {
  const mapper = new DaypasswordApiPayloadMapper();
  const base = (): DaypasswordEnrollmentData => ({
    ...common,
    type: "daypassword",
    otpKey: "K",
    otpLength: 8,
    hashAlgorithm: "sha1",
    timeStep: "12h",
    generateOnServer: false
  });

  it("maps and coerces number-like fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.otplen).toBe(8);
    expect(p.hashlib).toBe("sha1");
    expect(p.timeStep).toBe("12h");
    expect("serial" in p).toBe(false);
  });

  it("drops undefined optionals", () => {
    const d = { ...base(), otpKey: undefined, otpLength: undefined, hashAlgorithm: undefined, timeStep: undefined };
    const p = mapper.toApiPayload(d);
    expect("otpkey" in p).toBe(false);
    expect("otplen" in p).toBe(false);
    expect("hashlib" in p).toBe(false);
    expect("timeStep" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to DaypasswordEnrollmentData", () => {
    const details = {
      tokentype: "daypassword",
      description: "desc",
      container_serial: "CONT-1",
      info: { hashlib: "sha256", timeStep: "24h" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1",
      otplen: 8
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("daypassword");
    expect(result.serial).toBe("S1");
    expect(result.hashAlgorithm).toBe("sha256");
    expect(result.timeStep).toBe("24h");
    expect(result.otpLength).toBe(8);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to DaypasswordEnrollmentData defaults", () => {
    const details = {
      tokentype: "daypassword",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("daypassword");
    expect(result.serial).toBe("S1");
    expect(result.hashAlgorithm).toBeUndefined();
    expect(result.timeStep).toBeUndefined();
    expect(result.otpLength).toBeUndefined();
  });
});

describe("EmailApiPayloadMapper", () => {
  const mapper = new EmailApiPayloadMapper();
  const base = (): EmailEnrollmentData => ({
    ...common,
    type: "email",
    emailAddress: "a@b.c",
    readEmailDynamically: true
  });

  it("maps email and dynamic flag", () => {
    const p = mapper.toApiPayload(base());
    expect(p.email).toBe("a@b.c");
    expect(p.dynamic_email).toBe(true);
  });

  it("omits email if undefined", () => {
    const d = { ...base(), emailAddress: undefined };
    const p = mapper.toApiPayload(d);
    expect("email" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to EmailEnrollmentData", () => {
    const details = {
      tokentype: "email",
      description: "desc",
      container_serial: "CONT-1",
      info: { email: "test@example.com" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("email");
    expect(result.serial).toBe("S1");
    expect(result.emailAddress).toBe("test@example.com");
    expect(result.readEmailDynamically).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to EmailEnrollmentData with dynamic mail", () => {
    const details = {
      tokentype: "email",
      description: "desc",
      container_serial: "CONT-1",
      info: { dynamic_email: true },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("email");
    expect(result.serial).toBe("S1");
    expect(result.emailAddress).toBeUndefined();
    expect(result.readEmailDynamically).toBe(true);
  });
});

describe("HotpApiPayloadMapper", () => {
  const mapper = new HotpApiPayloadMapper();
  const base = (): HotpEnrollmentData => ({
    ...common,
    type: "hotp",
    generateOnServer: false,
    otpKey: "K",
    otpLength: "8" as any,
    hashAlgorithm: "sha256",
    serial: null
  });

  it("maps with client key", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.genkey).toBe(0);
    expect(p.otplen).toBe(8);
    expect(p.hashlib).toBe("sha256");
    expect("serial" in p).toBe(false);
  });

  it("maps generateOnServer", () => {
    const d = { ...base(), generateOnServer: true };
    const p = mapper.toApiPayload(d);
    expect(p.otpkey).toBeNull();
    expect(p.genkey).toBe(1);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to HotpEnrollmentData", () => {
    const details = {
      tokentype: "hotp",
      description: "desc",
      container_serial: "CONT-1",
      info: { validity_period_start: "2025-01-01", validity_period_end: "2025-12-31", hashlib: "sha512" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1",
      otplen: 8
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("hotp");
    expect(result.description).toBe("desc");
    expect(result.containerSerial).toBe("CONT-1");
    expect(result.validityPeriodStart).toBe("2025-01-01");
    expect(result.validityPeriodEnd).toBe("2025-12-31");
    expect(result.user).toBe("alice");
    expect(result.realm).toBe("realm1");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBe(8);
    expect(result.hashAlgorithm).toBe("sha512");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to HotpEnrollmentData defaults", () => {
    const details = {
      tokentype: "hotp",
      description: "desc",
      container_serial: "CONT-1",
      info: { validity_period_start: "2025-01-01", validity_period_end: "2025-12-31" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("hotp");
    expect(result.description).toBe("desc");
    expect(result.containerSerial).toBe("CONT-1");
    expect(result.validityPeriodStart).toBe("2025-01-01");
    expect(result.validityPeriodEnd).toBe("2025-12-31");
    expect(result.user).toBe("alice");
    expect(result.realm).toBe("realm1");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBeUndefined();
    expect(result.hashAlgorithm).toBeUndefined();
  });
});

describe("IndexedSecretApiPayloadMapper", () => {
  const mapper = new IndexedSecretApiPayloadMapper();
  const base = (): IndexedSecretEnrollmentData => ({ ...common, type: "indexedsecret", otpKey: "K" });

  it("maps otpkey", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
  });

  it("drops otpkey if undefined", () => {
    const d = { ...base(), otpKey: undefined };
    const p = mapper.toApiPayload(d);
    expect("otpkey" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to IndexedSecretEnrollmentData", () => {
    const details = {
      tokentype: "indexedsecret",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("indexedsecret");
    expect(result.serial).toBe("S1");
  });
});

describe("MotpApiPayloadMapper", () => {
  const mapper = new MotpApiPayloadMapper();
  const base = (): MotpEnrollmentData => ({
    ...common,
    type: "motp",
    generateOnServer: false,
    otpKey: "K",
    motpPin: "9999"
  });

  it("maps with client key and motppin", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.genkey).toBe(0);
    expect(p.motppin).toBe("9999");
    expect("serial" in p).toBe(false);
  });

  it("maps generateOnServer", () => {
    const d = { ...base(), generateOnServer: true };
    const p = mapper.toApiPayload(d);
    expect(p.otpkey).toBeNull();
    expect(p.genkey).toBe(1);
  });

  it("drops motppin if undefined", () => {
    const d = { ...base(), motpPin: undefined };
    const p = mapper.toApiPayload(d);
    expect("motppin" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to MotpEnrollmentData", () => {
    const details = {
      tokentype: "motp",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("motp");
    expect(result.serial).toBe("S1");
  });
});

describe("PaperApiPayloadMapper", () => {
  const mapper = new PaperApiPayloadMapper();
  const base = (): PaperEnrollmentData => ({
    ...common,
    type: "paper",
    otpLength: 6,
    otpCount: 10,
    serial: "S1"
  });

  it("maps fields and keeps serial if present", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otplen).toBe(6);
    expect(p.otpcount).toBe(10);
    expect(p.serial).toBe("S1");
  });

  it("drops undefined and null serial", () => {
    const d = { ...base(), otpLength: undefined, otpCount: undefined, serial: null };
    const p = mapper.toApiPayload(d);
    expect("otplen" in p).toBe(false);
    expect("otpcount" in p).toBe(false);
    expect("serial" in p).toBe(false);
  });

  it("fromApiPayload maps back", () => {
    const result = mapper.fromApiPayload({ otplen: 7, otpcount: 20 });
    expect(result.otpLength).toBe(7);
    expect(result.otpCount).toBe(20);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to PaperEnrollmentData", () => {
    const details = {
      tokentype: "paper",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1",
      otplen: 8
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("paper");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBe(8);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to PaperEnrollmentData defaults", () => {
    const details = {
      tokentype: "paper",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("paper");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBeUndefined();
  });
});

describe("PasskeyApiPayloadMapper", () => {
  const mapper = new PasskeyApiPayloadMapper();
  const base = (): PasskeyEnrollmentData => ({ ...common, type: "passkey" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("passkey");
  });

  it("respects onlyAddToRealm", () => {
    const d = { ...base(), onlyAddToRealm: true };
    const p = mapper.toApiPayload(d);
    expect(p.user).toBeNull();
    expect(p.realm).toBe("realm1");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to PasskeyEnrollmentData", () => {
    const details = {
      tokentype: "passkey",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("passkey");
  });
});

describe("PasskeyFinalizeApiPayloadMapper", () => {
  const mapper = new PasskeyFinalizeApiPayloadMapper();
  const base = (): PasskeyFinalizeData => ({
    ...common,
    type: "passkey",
    credential_id: "cid",
    attestationObject: "att",
    clientDataJSON: "cd",
    rawId: "raw",
    authenticatorAttachment: "platform",
    transaction_id: "tx",
    serial: "S1"
  });

  it("maps finalize payload", () => {
    const p = mapper.toApiPayload(base());
    expect(p.credential_id).toBe("cid");
    expect(p.serial).toBe("S1");
    expect(p.transaction_id).toBe("tx");
  });

  it("includes credProps when present", () => {
    const d = { ...base(), credProps: { rk: true } };
    const p = mapper.toApiPayload(d);
    expect(p.credProps).toEqual({ rk: true });
  });
});

describe("PushApiPayloadMapper", () => {
  const mapper = new PushApiPayloadMapper();
  const base = (): PushEnrollmentData => ({ ...common, type: "push" });

  it("maps with genkey=1", () => {
    const p = mapper.toApiPayload(base());
    expect(p.genkey).toBe(1);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to PushEnrollmentData", () => {
    const details = {
      tokentype: "push",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("push");
    expect(result.serial).toBe("S1");
  });
});

describe("QuestionApiPayloadMapper", () => {
  const mapper = new QuestionApiPayloadMapper();
  const base = (): QuestionEnrollmentData => ({
    ...common,
    type: "question",
    answers: { q1: "a1", q2: "a2" }
  });

  it("maps answers to questions", () => {
    const p = mapper.toApiPayload(base());
    expect(p.questions).toEqual({ q1: "a1", q2: "a2" });
  });

  it("drops questions if undefined", () => {
    const d = { ...base(), answers: undefined };
    const p = mapper.toApiPayload(d);
    expect("questions" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to QuestionEnrollmentData", () => {
    const details = {
      tokentype: "question",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("question");
    expect(result.serial).toBe("S1");
  });
});

describe("RadiusApiPayloadMapper", () => {
  const mapper = new RadiusApiPayloadMapper();
  const base = (): RadiusEnrollmentData => ({
    ...common,
    type: "radius",
    radiusServerConfiguration: "cfg1",
    radiusUser: "bob"
  });

  it("maps radius fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p["radius.identifier"]).toBe("cfg1");
    expect(p["radius.user"]).toBe("bob");
  });

  it("drops undefined radius fields", () => {
    const d = { ...base(), radiusServerConfiguration: undefined, radiusUser: undefined };
    const p = mapper.toApiPayload(d);
    expect("radius.identifier" in p).toBe(false);
    expect("radius.user" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to RadiusEnrollmentData", () => {
    const details = {
      tokentype: "radius",
      description: "desc",
      container_serial: "CONT-1",
      info: { "radius.identifier": "radius1", "radius.user": "test-user" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("radius");
    expect(result.serial).toBe("S1");
    expect(result.radiusServerConfiguration).toBe("radius1");
    expect(result.radiusUser).toBe("test-user");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to RadiusEnrollmentData", () => {
    const details = {
      tokentype: "radius",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("radius");
    expect(result.serial).toBe("S1");
    expect(result.radiusServerConfiguration).toBe("");
    expect(result.radiusUser).toBe("");
  });
});

describe("RegistrationApiPayloadMapper", () => {
  const mapper = new RegistrationApiPayloadMapper();
  const base = (): RegistrationEnrollmentData => ({ ...common, type: "registration", serial: "S1" });

  it("maps serial and drops null", () => {
    const p = mapper.toApiPayload(base());
    expect(p.serial).toBe("S1");
    const p2 = mapper.toApiPayload({ ...base(), serial: null });
    expect("serial" in p2).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to RegistrationEnrollmentData", () => {
    const details = {
      tokentype: "registration",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("registration");
    expect(result.serial).toBe("S1");
  });
});

describe("RemoteApiPayloadMapper", () => {
  const mapper = new RemoteApiPayloadMapper();
  const base = (): RemoteEnrollmentData => ({
    ...common,
    type: "remote",
    remoteServer: { id: "srv1" } as any,
    remoteSerial: "RS",
    remoteUser: "ru",
    remoteRealm: "rr",
    remoteResolver: "res",
    checkPinLocally: true
  });

  it("maps all remote fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p["remote.server_id"]).toBe("srv1");
    expect(p["remote.serial"]).toBe("RS");
    expect(p["remote.user"]).toBe("ru");
    expect(p["remote.realm"]).toBe("rr");
    expect(p["remote.resolver"]).toBe("res");
    expect(p["remote.local_checkpin"]).toBe(true);
  });

  it("sets server id null when server missing", () => {
    const d = { ...base(), remoteServer: null };
    const p = mapper.toApiPayload(d);
    expect(p["remote.server_id"]).toBeNull();
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to RemoteEnrollmentData", () => {
    const details = {
      tokentype: "remote",
      description: "desc",
      container_serial: "CONT-1",
      info: {
        "remote.server_id": "1234",
        "remote.serial": "s1",
        "remote.user": "Alice",
        "remote.realm": "another-realm",
        "remote.resolver": "resolver-1",
        "remote.local_checkpin": "True"
      },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("remote");
    expect(result.serial).toBe("S1");
    expect(result.remoteServer).toBe("1234");
    expect(result.remoteSerial).toBe("s1");
    expect(result.remoteUser).toBe("Alice");
    expect(result.remoteRealm).toBe("another-realm");
    expect(result.remoteResolver).toBe("resolver-1");
    expect(result.checkPinLocally).toBe(true);

    details.info["remote.local_checkpin"] = "False";
    const result2 = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result2.checkPinLocally).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to RemoteEnrollmentData defaults", () => {
    const details = {
      tokentype: "remote",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("remote");
    expect(result.serial).toBe("S1");
    expect(result.remoteServer).toBe("");
    expect(result.remoteSerial).toBe("");
    expect(result.remoteUser).toBe("");
    expect(result.remoteRealm).toBe("");
    expect(result.remoteResolver).toBe("");
    expect(result.checkPinLocally).toBe(false);
  });
});

describe("SmsApiPayloadMapper", () => {
  const mapper = new SmsApiPayloadMapper();
  const base = (): SmsEnrollmentData => ({
    ...common,
    type: "sms",
    smsGateway: "gw",
    phoneNumber: "123",
    readNumberDynamically: false
  });

  it("maps phone, gateway, dynamic", () => {
    const p = mapper.toApiPayload(base());
    expect(p["sms.identifier"]).toBe("gw");
    expect(p.phone).toBe("123");
    expect(p.dynamic_phone).toBe(false);
  });

  it("dynamic phone nulls phone and sets flag", () => {
    const d = { ...base(), readNumberDynamically: true };
    const p = mapper.toApiPayload(d);
    expect(p.phone).toBeNull();
    expect(p.dynamic_phone).toBe(true);
  });

  it("drops undefined keys", () => {
    const d = { ...base(), smsGateway: undefined, readNumberDynamically: undefined };
    const p = mapper.toApiPayload(d);
    expect("sms.identifier" in p).toBe(false);
    expect("dynamic_phone" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to SmsEnrollmentData", () => {
    const details = {
      tokentype: "sms",
      description: "desc",
      container_serial: "CONT-1",
      info: { "sms.identifier": "1234", phone: "0123456789" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("sms");
    expect(result.serial).toBe("S1");
    expect(result.smsGateway).toBe("1234");
    expect(result.phoneNumber).toBe("0123456789");
    expect(result.readNumberDynamically).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to SmsEnrollmentData dynamic phone", () => {
    const details = {
      tokentype: "sms",
      description: "desc",
      container_serial: "CONT-1",
      info: { "sms.identifier": "1234", dynamic_phone: "True" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("sms");
    expect(result.serial).toBe("S1");
    expect(result.smsGateway).toBe("1234");
    expect(result.phoneNumber).toBeUndefined();
    expect(result.readNumberDynamically).toBe(true);

    details.info.dynamic_phone = "False";
    const result2 = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result2.readNumberDynamically).toBe(false);
  });
});

describe("SpassApiPayloadMapper", () => {
  const mapper = new SpassApiPayloadMapper();
  const base = (): SpassEnrollmentData => ({ ...common, type: "spass" });

  it("maps base fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("spass");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to SpassEnrollmentData", () => {
    const details = {
      tokentype: "spass",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("spass");
    expect(result.serial).toBe("S1");
  });
});

describe("SshkeyApiPayloadMapper", () => {
  const mapper = new SshkeyApiPayloadMapper();
  const base = (): SshkeyEnrollmentData => ({ ...common, type: "sshkey", sshPublicKey: "ssh-rsa AAA..." });

  it("maps sshkey", () => {
    const p = mapper.toApiPayload(base());
    expect(p.sshkey).toBe("ssh-rsa AAA...");
  });

  it("drops sshkey if undefined", () => {
    const d = { ...base(), sshPublicKey: undefined };
    const p = mapper.toApiPayload(d);
    expect("sshkey" in p).toBe(false);
  });

  it("fromApiPayload maps back to sshPublicKey", () => {
    const r = mapper.fromApiPayload({ sshkey: "K", type: "sshkey" });
    expect(r.sshPublicKey).toBe("K");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to SshkeyEnrollmentData", () => {
    const details = {
      tokentype: "sshkey",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("sshkey");
    expect(result.serial).toBe("S1");
  });
});

describe("TanApiPayloadMapper", () => {
  const mapper = new TanApiPayloadMapper();
  const base = (): TanEnrollmentData => ({ ...common, type: "tan", tanCount: 50, tanLength: 10, serial: "S1" });

  it("maps fields and serial", () => {
    const p = mapper.toApiPayload(base());
    expect(p.tancount).toBe(50);
    expect(p.tanlength).toBe(10);
    expect(p.serial).toBe("S1");
  });

  it("drops undefined and null serial", () => {
    const d = { ...base(), tanCount: undefined, tanLength: undefined, serial: null };
    const p = mapper.toApiPayload(d);
    expect("tancount" in p).toBe(false);
    expect("tanlength" in p).toBe(false);
    expect("serial" in p).toBe(false);
  });

  it("fromApiPayload maps back", () => {
    const r = mapper.fromApiPayload({ tancount: 5, tanlength: 6 });
    expect(r.tanCount).toBe(5);
    expect(r.tanLength).toBe(6);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to TanEnrollmentData", () => {
    const details = {
      tokentype: "tan",
      description: "desc",
      container_serial: "CONT-1",
      info: { "tan.count": 100 },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("tan");
    expect(result.serial).toBe("S1");
    expect(result.tanCount).toBe(100);
  });
});

describe("TiqrApiPayloadMapper", () => {
  const mapper = new TiqrApiPayloadMapper();
  const base = (): TiqrEnrollmentData => ({ ...common, type: "tiqr" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("tiqr");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to TiqrEnrollmentData", () => {
    const details = {
      tokentype: "tiqr",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("tiqr");
    expect(result.serial).toBe("S1");
  });
});

describe("TotpApiPayloadMapper", () => {
  const mapper = new TotpApiPayloadMapper();
  const base = (): TotpEnrollmentData => ({
    ...common,
    type: "totp",
    generateOnServer: false,
    otpKey: "K",
    otpLength: "6" as any,
    hashAlgorithm: "sha1",
    timeStep: "30" as any,
    serial: "S1"
  });

  it("maps client key and coerces numbers", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.genkey).toBe(0);
    expect(p.otplen).toBe(6);
    expect(p.hashlib).toBe("sha1");
    expect(p.timeStep).toBe(30);
    expect(p.serial).toBe("S1");
  });

  it("generateOnServer nulls otpkey and sets genkey", () => {
    const d = { ...base(), generateOnServer: true };
    const p = mapper.toApiPayload(d);
    expect(p.otpkey).toBeNull();
    expect(p.genkey).toBe(1);
  });

  it("drops undefined and null serial", () => {
    const d = { ...base(), otpLength: undefined, hashAlgorithm: undefined, timeStep: undefined, serial: null };
    const p = mapper.toApiPayload(d);
    expect("otplen" in p).toBe(false);
    expect("hashlib" in p).toBe(false);
    expect("timeStep" in p).toBe(false);
    expect("serial" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to TotpEnrollmentData", () => {
    const details = {
      tokentype: "totp",
      description: "desc",
      container_serial: "CONT-1",
      info: { hashlib: "sha256", timeStep: "60" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1",
      otplen: 8
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("totp");
    expect(result.serial).toBe("S1");
    expect(result.hashAlgorithm).toBe("sha256");
    expect(result.timeStep).toBe(60);
    expect(result.otpLength).toBe(8);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to TotpEnrollmentData, defaults", () => {
    const details = {
      tokentype: "totp",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("totp");
    expect(result.serial).toBe("S1");
    expect(result.hashAlgorithm).toBeUndefined();
    expect(result.timeStep).toBeUndefined();
    expect(result.otpLength).toBeUndefined();
  });
});

describe("U2fApiPayloadMapper", () => {
  const mapper = new U2fApiPayloadMapper();
  const base = (): U2fEnrollmentData => ({ ...common, type: "u2f" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("u2f");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to U2fEnrollmentData", () => {
    const details = {
      tokentype: "u2f",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("u2f");
    expect(result.serial).toBe("S1");
  });
});

describe("VascoApiPayloadMapper", () => {
  const mapper = new VascoApiPayloadMapper();
  const base = (): VascoEnrollmentData => ({
    ...common,
    type: "vasco",
    useVascoSerial: true,
    vascoSerial: "VS1",
    otpKey: "K"
  });

  it("maps serial when useVascoSerial", () => {
    const p = mapper.toApiPayload(base());
    expect(p.serial).toBe("VS1");
  });

  it("drops serial when not using vasco serial", () => {
    const d = { ...base(), useVascoSerial: false };
    const p = mapper.toApiPayload(d);
    expect("serial" in p).toBe(false);
  });

  it("drops otpkey if undefined", () => {
    const d = { ...base(), otpKey: undefined };
    const p = mapper.toApiPayload(d);
    expect("otpkey" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to VascoEnrollmentData", () => {
    const details = {
      tokentype: "vasco",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("vasco");
    expect(result.serial).toBe("S1");
  });
});

describe("WebAuthnApiPayloadMapper", () => {
  const mapper = new WebAuthnApiPayloadMapper();
  const base = (): WebAuthnEnrollmentData => ({ ...common, type: "webauthn" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("webauthn");
  });

  it("adds credential_id when present", () => {
    const p = mapper.toApiPayload({ ...base(), credential_id: "CID" });
    expect(p.credential_id).toBe("CID");
  });

  it("drops credential_id when undefined", () => {
    const p = mapper.toApiPayload(base());
    expect("credential_id" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to WebAuthnEnrollmentData", () => {
    const details = {
      tokentype: "webauthn",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("webauthn");
    expect(result.serial).toBe("S1");
  });
});

describe("WebAuthnFinalizeApiPayloadMapper", () => {
  const mapper = new WebAuthnFinalizeApiPayloadMapper();
  const base = (): WebauthnFinalizeData => ({
    ...common,
    type: "webauthn",
    transaction_id: "T1",
    serial: "S1",
    credential_id: "CID",
    rawId: "RAW",
    authenticatorAttachment: null,
    regdata: "REG",
    clientdata: "CL"
  });

  it("maps finalize", () => {
    const p = mapper.toApiPayload(base());
    expect(p.transaction_id).toBe("T1");
    expect(p.serial).toBe("S1");
    expect(p.credential_id).toBe("CID");
  });

  it("includes credProps when present", () => {
    const d = { ...base(), credProps: { rk: true } };
    const p = mapper.toApiPayload(d);
    expect(p.credProps).toEqual({ rk: true });
  });
});

describe("YubicoApiPayloadMapper", () => {
  const mapper = new YubicoApiPayloadMapper();
  const base = (): YubicoEnrollmentData => ({ ...common, type: "yubico", yubicoIdentifier: "YID" });

  it("maps yubico id", () => {
    const p = mapper.toApiPayload(base());
    expect(p["yubico.tokenid"]).toBe("YID");
  });

  it("drops when undefined", () => {
    const p = mapper.toApiPayload({ ...base(), yubicoIdentifier: undefined });
    expect("yubico.tokenid" in p).toBe(false);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to YubicoEnrollmentData", () => {
    const details = {
      tokentype: "yubico",
      description: "desc",
      container_serial: "CONT-1",
      info: { "yubico.tokenid": "1234" },
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("yubico");
    expect(result.serial).toBe("S1");
    expect(result.yubicoIdentifier).toBe("1234");
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to YubicoEnrollmentData defaults", () => {
    const details = {
      tokentype: "yubico",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("yubico");
    expect(result.serial).toBe("S1");
    expect(result.yubicoIdentifier).toBeUndefined();
  });
});

describe("YubikeyApiPayloadMapper", () => {
  const mapper = new YubikeyApiPayloadMapper();
  const base = (): YubikeyEnrollmentData => ({ ...common, type: "yubikey", otpKey: "K", otpLength: 44 });

  it("maps nullable fields as-is", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.otplen).toBe(44);
  });

  it("keeps nulls", () => {
    const p = mapper.toApiPayload({ ...base(), otpKey: null, otpLength: null });
    expect(p.otpkey).toBeNull();
    expect(p.otplen).toBeNull();
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to YubikeyEnrollmentData", () => {
    const details = {
      tokentype: "yubikey",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1",
      otplen: 38
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("yubikey");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBe(38);
  });

  it("fromTokenDetailsToEnrollmentData maps TokenDetails to YubikeyEnrollmentData defaults", () => {
    const details = {
      tokentype: "yubikey",
      description: "desc",
      container_serial: "CONT-1",
      info: {},
      username: "alice",
      realms: ["realm1"],
      serial: "S1"
    };
    const result = mapper.fromTokenDetailsToEnrollmentData(details as any);
    expect(result.type).toBe("yubikey");
    expect(result.serial).toBe("S1");
    expect(result.otpLength).toBeNull();
  });
});

