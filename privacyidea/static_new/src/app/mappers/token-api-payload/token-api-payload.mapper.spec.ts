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
import { ApplspecApiPayloadMapper } from "./applspec-token-api-payload.mapper";
import { CertificateApiPayloadMapper } from "./certificate-token-api-payload.mapper";
import { DaypasswordApiPayloadMapper } from "./daypassword-token-api-payload.mapper";
import { EmailApiPayloadMapper } from "./email-token-api-payload.mapper";
import { HotpApiPayloadMapper } from "./hotp-token-api-payload.mapper";
import { IndexedSecretApiPayloadMapper } from "./indexedsecret-token-api-payload.mapper";
import { MotpApiPayloadMapper } from "./motp-token-api-payload.mapper";
import { PaperApiPayloadMapper } from "./paper-token-api-payload.mapper";
import { PasskeyApiPayloadMapper, PasskeyFinalizeApiPayloadMapper } from "./passkey-token-api-payload.mapper";
import { PushApiPayloadMapper } from "./push-token-api-payload.mapper";
import { QuestionApiPayloadMapper } from "./question-token-api-payload.mapper";
import { RadiusApiPayloadMapper } from "./radius-token-api-payload.mapper";
import { RegistrationApiPayloadMapper } from "./registration-token-api-payload.mapper";
import { RemoteApiPayloadMapper } from "./remote-token-api-payload.mapper";
import { SmsApiPayloadMapper } from "./sms-token-api-payload.mapper";
import { SpassApiPayloadMapper } from "./spass-token-api-payload.mapper";
import { SshkeyApiPayloadMapper } from "./sshkey-token-api-payload.mapper";
import { TanApiPayloadMapper } from "./tan-token-api-payload.mapper";
import { TiqrApiPayloadMapper } from "./tiqr-token-api-payload.mapper";
import { TotpApiPayloadMapper } from "./totp-token-api-payload.mapper";
import { U2fApiPayloadMapper } from "./u2f-token-api-payload.mapper";
import { VascoApiPayloadMapper } from "./vasco-token-api-payload.mapper";
import { WebAuthnApiPayloadMapper, WebAuthnFinalizeApiPayloadMapper } from "./webauthn-token-api-payload.mapper";
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
    expect(payload.realm).toBeNull();
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
});

describe("DaypasswordApiPayloadMapper", () => {
  const mapper = new DaypasswordApiPayloadMapper();
  const base = (): DaypasswordEnrollmentData => ({
    ...common,
    type: "daypassword",
    otpKey: "K",
    otpLength: 8,
    hashAlgorithm: "sha1",
    timeStep: "60",
    generateOnServer: false
  });

  it("maps and coerces number-like fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p.otpkey).toBe("K");
    expect(p.otplen).toBe(8);
    expect(p.hashlib).toBe("sha1");
    expect(p.timeStep).toBe(60);
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
});

describe("SpassApiPayloadMapper", () => {
  const mapper = new SpassApiPayloadMapper();
  const base = (): SpassEnrollmentData => ({ ...common, type: "spass" });

  it("maps base fields", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("spass");
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
});

describe("TiqrApiPayloadMapper", () => {
  const mapper = new TiqrApiPayloadMapper();
  const base = (): TiqrEnrollmentData => ({ ...common, type: "tiqr" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("tiqr");
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
});

describe("U2fApiPayloadMapper", () => {
  const mapper = new U2fApiPayloadMapper();
  const base = (): U2fEnrollmentData => ({ ...common, type: "u2f" });

  it("maps base", () => {
    const p = mapper.toApiPayload(base());
    expect(p.type).toBe("u2f");
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
});
