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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { LdapMachineResolverData, MachineResolverData } from "@services/machine-resolver/machine-resolver.service";
import { MachineResolverLdapTabComponent } from "./machine-resolver-ldap-tab.component";

const completeData = (): LdapMachineResolverData => ({
  type: "ldap",
  resolver: "ldap1",
  LDAPURI: "ldap://test",
  LDAPBASE: "dc=test",
  BINDDN: "cn=admin",
  BINDPW: "password",
  AUTHTYPE: "Simple",
  TLS_VERIFY: true,
  TLS_CA_FILE: "/ca.crt",
  TIMEOUT: "7",
  SIZELIMIT: "100",
  SEARCHFILTER: "(a=b)",
  IDATTRIBUTE: "DN",
  IPATTRIBUTE: "ip",
  HOSTNAMEATTRIBUTE: "host",
  NOREFERRALS: "False"
});

describe("MachineResolverLdapTabComponent", () => {
  let component: MachineResolverLdapTabComponent;
  let fixture: ComponentFixture<MachineResolverLdapTabComponent>;
  let emitted: MachineResolverData[];

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const setData = async (data: MachineResolverData) => {
    fixture.componentRef.setInput("machineResolverData", data);
    await flush();
  };
  const input = (placeholder: string) =>
    fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  const type = async (el: HTMLInputElement, value: string) => {
    el.value = value;
    el.dispatchEvent(new Event("input"));
    await flush();
  };
  const checkbox = (index: number) =>
    fixture.nativeElement.querySelectorAll("mat-checkbox input")[index] as HTMLInputElement;
  const kinds = (field: { errors: () => { kind: string }[] }) => field.errors().map((e) => e.kind);
  const lastEmitted = () => emitted[emitted.length - 1] as LdapMachineResolverData;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverLdapTabComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverLdapTabComponent);
    component = fixture.componentInstance;
    emitted = [];
    component.newData.subscribe((data) => emitted.push(data));
    fixture.componentRef.setInput("canEdit", true);
    fixture.componentRef.setInput("machineResolverData", { type: "ldap", resolver: "test" } as LdapMachineResolverData);
    await flush();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("form model", () => {
    it("shows empty fields and the default timeout for data without values, and emits nothing", () => {
      expect(component.model()).toEqual({
        LDAPURI: "",
        TLS_VERIFY: false,
        TLS_CA_FILE: "",
        LDAPBASE: "",
        BINDDN: "",
        BINDPW: "",
        AUTHTYPE: "",
        TIMEOUT: "5",
        SIZELIMIT: "",
        NOREFERRALS: false,
        IDATTRIBUTE: "",
        SEARCHFILTER: "",
        HOSTNAMEATTRIBUTE: "",
        IPATTRIBUTE: ""
      });
      expect(input("5").value).toBe("5");
      expect(emitted).toEqual([]);
    });

    it("shows every value of the data and emits nothing", async () => {
      await setData(completeData());
      expect(input("ldap://privacyidea.server1, ldap://privacyidea.server2").value).toBe("ldap://test");
      expect(input("/etc/privacyidea/ldap-ca.crt").value).toBe("/ca.crt");
      expect(input("ou=users,dc=domain,dc=tld").value).toBe("dc=test");
      expect(input("cn=admin,ou=users,dc=domain,dc=tld").value).toBe("cn=admin");
      expect(input("topsecret").value).toBe("password");
      expect(input("5").value).toBe("7");
      expect(input("500").value).toBe("100");
      expect(input("DN").value).toBe("DN");
      expect(input("(objectClass=computer)").value).toBe("(a=b)");
      expect(input("dNSHostName").value).toBe("host");
      expect(checkbox(0).checked).toBe(true);
      expect(checkbox(1).checked).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-select").textContent).toContain("simple");
      expect(emitted).toEqual([]);
    });

    it("maps the referral flag from the string values", async () => {
      await setData({ ...completeData(), NOREFERRALS: "True" } as LdapMachineResolverData);
      expect(checkbox(1).checked).toBe(true);
    });
  });

  describe("validity", () => {
    it("is invalid while a required field is empty", () => {
      expect(component.isValid()).toBe(false);
    });

    it("is valid with the four required fields", async () => {
      await setData(completeData());
      expect(component.isValid()).toBe(true);
    });

    it.each(["LDAPURI", "LDAPBASE", "BINDDN", "BINDPW"] as const)("requires %s", async (key) => {
      await setData({ ...completeData(), [key]: "" });
      expect(component.isValid()).toBe(false);
      expect(kinds(component.ldapForm[key]())).toEqual(["required"]);
    });

    it.each(["LDAPURI", "LDAPBASE", "BINDDN", "BINDPW"] as const)("rejects a blank %s", async (key) => {
      await setData({ ...completeData(), [key]: " " });
      expect(component.isValid()).toBe(false);
      expect(kinds(component.ldapForm[key]())).toEqual(["required"]);
    });

    it("renders the required messages once every field is touched", async () => {
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
      await component.touchAll();
      await flush();
      const messages = Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map(
        (e) => (e as HTMLElement).textContent
      );
      expect(messages).toHaveLength(4);
      expect(messages.join(" ")).toContain("Server URI is required");
      expect(messages.join(" ")).toContain("Base DN is required");
      expect(messages.join(" ")).toContain("Bind DN is required");
      expect(messages.join(" ")).toContain("Bind password is required");
    });

    it("renders a required message for the field the user emptied", async () => {
      await setData(completeData());
      await type(input("topsecret"), "");
      component.ldapForm.BINDPW().markAsTouched();
      await flush();
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Bind password is required");
    });

    it("reports a parse error for a number input holding text and renders its message", async () => {
      await setData(completeData());
      const timeout = input("5");
      Object.defineProperty(timeout, "validity", { configurable: true, get: () => ({ badInput: true }) });
      await type(timeout, "");
      expect(kinds(component.ldapForm.TIMEOUT())).toEqual(["parse"]);
      expect(component.isValid()).toBe(false);
      component.ldapForm.TIMEOUT().markAsTouched();
      await flush();
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
    });

    it("renders the parse message of the size limit", async () => {
      await setData(completeData());
      const sizeLimit = input("500");
      Object.defineProperty(sizeLimit, "validity", { configurable: true, get: () => ({ badInput: true }) });
      await type(sizeLimit, "");
      expect(kinds(component.ldapForm.SIZELIMIT())).toEqual(["parse"]);
      component.ldapForm.SIZELIMIT().markAsTouched();
      await flush();
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
    });
  });

  describe("canEdit", () => {
    it("disables every control and counts the form as valid when editing is not allowed", async () => {
      fixture.componentRef.setInput("canEdit", false);
      await flush();
      const inputs = Array.from(fixture.nativeElement.querySelectorAll("input")) as HTMLInputElement[];
      expect(inputs.length).toBeGreaterThan(0);
      expect(inputs.every((el) => el.disabled)).toBe(true);
      expect(component.ldapForm().disabled()).toBe(true);
      expect(component.isValid()).toBe(true);
      expect(fixture.nativeElement.querySelector("button")).toBeNull();
    });

    it("enables the controls when editing is allowed", () => {
      expect(input("ldap://privacyidea.server1, ldap://privacyidea.server2").disabled).toBe(false);
      expect(input("topsecret").disabled).toBe(false);
    });
  });

  describe("TLS CA file", () => {
    it("is disabled while TLS Verify is off", () => {
      expect(input("/etc/privacyidea/ldap-ca.crt").disabled).toBe(true);
      expect(component.ldapForm.TLS_CA_FILE().disabled()).toBe(true);
    });

    it("is enabled once TLS Verify is checked", async () => {
      checkbox(0).click();
      await flush();
      expect(component.model().TLS_VERIFY).toBe(true);
      expect(input("/etc/privacyidea/ldap-ca.crt").disabled).toBe(false);
    });

    it("is dropped from the emitted data when TLS Verify is unchecked", async () => {
      await setData(completeData());
      checkbox(0).click();
      await flush();
      const data = lastEmitted();
      expect(data.TLS_VERIFY).toBe(false);
      expect("TLS_CA_FILE" in data).toBe(false);
    });

    it("is part of the emitted data while TLS Verify is on", async () => {
      await setData(completeData());
      await type(input("/etc/privacyidea/ldap-ca.crt"), "/other.crt");
      expect(lastEmitted().TLS_CA_FILE).toBe("/other.crt");
      expect(lastEmitted().TLS_VERIFY).toBe(true);
    });
  });

  describe("emitted data", () => {
    it("merges a typed value into the data of the input and sets the type", async () => {
      await setData(completeData());
      await type(input("ldap://privacyidea.server1, ldap://privacyidea.server2"), "ldap://updated");
      expect(emitted).toEqual([{ ...completeData(), LDAPURI: "ldap://updated" }]);
    });

    it("leaves keys absent that the data did not hold and the user did not fill", async () => {
      await type(input("ldap://privacyidea.server1, ldap://privacyidea.server2"), "ldap://new");
      expect(emitted).toEqual([{ type: "ldap", resolver: "test", LDAPURI: "ldap://new" }]);
    });

    it("does not add the displayed default timeout to the data", async () => {
      await type(input("topsecret"), "pw");
      expect("TIMEOUT" in lastEmitted()).toBe(false);
    });

    it("emits an emptied timeout as an empty string", async () => {
      await type(input("5"), "");
      expect(lastEmitted().TIMEOUT).toBe("");
      await setData(lastEmitted());
      expect(input("5").value).toBe("");
      expect(emitted).toHaveLength(1);
    });

    it("emits a typed number as a string", async () => {
      await type(input("500"), "42");
      expect(lastEmitted().SIZELIMIT).toBe("42");
    });

    it("emits the selected bind type", async () => {
      component.model.update((m) => ({ ...m, AUTHTYPE: "SASL Digest-MD5" }));
      await flush();
      expect(lastEmitted().AUTHTYPE).toBe("SASL Digest-MD5");
    });

    it("emits the referral flag as the strings True and False", async () => {
      checkbox(1).click();
      await flush();
      expect(lastEmitted().NOREFERRALS).toBe("True");
      await setData(lastEmitted());
      checkbox(1).click();
      await flush();
      expect(lastEmitted().NOREFERRALS).toBe("False");
    });

    it("keeps the referral flag absent while it was absent and stays unchecked", async () => {
      await type(input("topsecret"), "pw");
      expect("NOREFERRALS" in lastEmitted()).toBe(false);
      expect("TLS_VERIFY" in lastEmitted()).toBe(false);
    });

    it("emits once per edit when the parent feeds the emitted data back", async () => {
      await type(input("topsecret"), "a");
      await setData(lastEmitted());
      expect(emitted).toHaveLength(1);
      await type(input("topsecret"), "ab");
      expect(emitted).toHaveLength(2);
      expect(lastEmitted().BINDPW).toBe("ab");
    });

    it("marks a typed field dirty and a checkbox click dirty", async () => {
      await type(input("topsecret"), "a");
      expect(component.ldapForm.BINDPW().dirty()).toBe(true);
      checkbox(0).click();
      await flush();
      expect(component.ldapForm.TLS_VERIFY().dirty()).toBe(true);
    });
  });

  describe("preassignActiveDirectoryAttributes", () => {
    it("fills the Active Directory attributes and emits them", async () => {
      component.preassignActiveDirectoryAttributes();
      await flush();
      expect(lastEmitted()).toEqual({
        type: "ldap",
        resolver: "test",
        SEARCHFILTER: "(objectClass=computer)",
        IDATTRIBUTE: "DN",
        HOSTNAMEATTRIBUTE: "dNSHostName",
        NOREFERRALS: "True"
      });
      expect(input("(objectClass=computer)").value).toBe("(objectClass=computer)");
      expect(checkbox(1).checked).toBe(true);
    });

    it("is offered by a button that runs it", async () => {
      const button = fixture.nativeElement.querySelector("button") as HTMLButtonElement;
      button.click();
      await flush();
      expect(lastEmitted().IDATTRIBUTE).toBe("DN");
    });
  });
});
