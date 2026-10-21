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
import { ComponentRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { LdapResolverComponent } from "./ldap-resolver.component";

describe("LdapResolverComponent", () => {
  let component: LdapResolverComponent;
  let componentRef: ComponentRef<LdapResolverComponent>;
  let fixture: ComponentFixture<LdapResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LdapResolverComponent],
      providers: [{ provide: ResolverService, useClass: MockResolverService }]
    }).compileComponents();

    fixture = TestBed.createComponent(LdapResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose isValid and getValue", () => {
    expect(typeof component.isValid).toBe("function");
    expect(typeof component.getValue).toBe("function");
  });

  it("should update model when data input changes", () => {
    componentRef.setInput("data", {
      LDAPURI: "ldap://localhost",
      LDAPBASE: "dc=example,dc=com",
      LOGINNAMEATTRIBUTE: "uid",
      LDAPSEARCHFILTER: "(objectClass=*)",
      USERINFO: "description"
    });

    fixture.detectChanges();

    expect(component.model().LDAPURI).toBe("ldap://localhost");
    expect(component.model().LDAPBASE).toBe("dc=example,dc=com");
    expect(component.model().LOGINNAMEATTRIBUTE).toBe("uid");
    expect(component.model().LDAPSEARCHFILTER).toBe("(objectClass=*)");
    expect(component.model().USERINFO).toBe("description");
  });

  it("should parse boolean and numeric strings from data input", () => {
    componentRef.setInput("data", {
      recursive_group_search: "False",
      TLS_VERIFY: "True",
      TIMEOUT: "5",
      EDITABLE: "False",
      group_base_dn: "ou=groups,dc=example,dc=com"
    });

    fixture.detectChanges();

    expect(component.model().recursive_group_search).toBe(false);
    expect(component.model().TLS_VERIFY).toBe(true);
    expect(component.model().TIMEOUT).toBe(5);
    expect(component.model().EDITABLE).toBe(false);
    expect(component.model().group_base_dn).toBe("ou=groups,dc=example,dc=com");
  });

  it("should parse '1' and '0' strings as booleans from data input", () => {
    componentRef.setInput("data", {
      recursive_group_search: "1",
      TLS_VERIFY: "0",
      EDITABLE: "1"
    });

    fixture.detectChanges();

    expect(component.model().recursive_group_search).toBe(true);
    expect(component.model().TLS_VERIFY).toBe(false);
    expect(component.model().EDITABLE).toBe(true);
  });

  it("should default TLS_VERSION to the negotiate protocol value", () => {
    expect(component.model().TLS_VERSION).toBe("2");
  });

  it("should coerce a numeric TLS_VERSION from data input to a string", () => {
    componentRef.setInput("data", { TLS_VERSION: 5 });

    fixture.detectChanges();

    expect(component.model().TLS_VERSION).toBe("5");
  });

  it("should show the keytab path of a SASL Kerberos bind in a plain text field", () => {
    componentRef.setInput("data", { AUTHTYPE: "SASL Kerberos", KEYTABFILE: "/etc/krb5/privacyidea.keytab" });

    fixture.detectChanges();

    const inputs: HTMLInputElement[] = Array.from(fixture.nativeElement.querySelectorAll("input"));
    const keytabInput = inputs.find((input) => input.value === "/etc/krb5/privacyidea.keytab");
    expect(keytabInput?.type).toBe("text");
    expect(fixture.nativeElement.querySelector("input[type='password']")).toBeNull();
  });

  it("should store a keytab path entered for a SASL Kerberos bind as KEYTABFILE", () => {
    componentRef.setInput("data", { AUTHTYPE: "SASL Kerberos" });
    fixture.detectChanges();

    const keytabInput: HTMLInputElement = fixture.nativeElement.querySelector(
      "input[placeholder='/etc/privacyidea/ldap.keytab']"
    );
    keytabInput.value = "/etc/krb5/privacyidea.keytab";
    keytabInput.dispatchEvent(new Event("input"));

    expect(component.getValue().KEYTABFILE).toBe("/etc/krb5/privacyidea.keytab");
    expect(component.getValue().BINDPW).toBe("");
  });

  it("should keep the bind password of a simple bind in a password field", () => {
    componentRef.setInput("data", { AUTHTYPE: "Simple", BINDPW: "secret" });

    fixture.detectChanges();

    const passwordInput: HTMLInputElement = fixture.nativeElement.querySelector("input[type='password']");
    expect(passwordInput.value).toBe("secret");
    expect(passwordInput.getAttribute("autocomplete")).toBe("new-password");
  });

  it("should apply LDAP presets", () => {
    const preset = component.ldapPresets[0];
    component.applyLdapPreset(preset);
    expect(component.model().LOGINNAMEATTRIBUTE).toBe(preset.loginName);
    expect(component.model().LDAPSEARCHFILTER).toBe(preset.searchFilter);
    expect(component.model().USERINFO).toBe(preset.userInfo);
    expect(component.model().UIDTYPE).toBe(preset.uidType);
    expect(component.model().MULTIVALUEATTRIBUTES).toBe("");
  });

  describe("TLS controls", () => {
    it("enables TLS version and verification for an ldaps URI", () => {
      componentRef.setInput("data", { LDAPURI: "ldaps://ldap.example.com", TLS_VERIFY: false, TLS_VERSION: "5" });
      fixture.detectChanges();

      expect(component.startTlsDisabled()).toBe(true);
      expect(component.tlsVersionDisabled()).toBe(false);
      expect(component.tlsVerifyDisabled()).toBe(false);
      // The CA file is used only with verification
      expect(component.tlsCaFileDisabled()).toBe(true);
    });

    it("enables the CA file for ldaps with verification", () => {
      componentRef.setInput("data", { LDAPURI: "ldaps://ldap.example.com", TLS_VERIFY: true });
      fixture.detectChanges();

      expect(component.tlsCaFileDisabled()).toBe(false);
      expect(component.ldapForm.TLS_CA_FILE().disabled()).toBe(false);
    });

    it("disables all TLS controls for ldap without STARTTLS, including the CA file input", () => {
      componentRef.setInput("data", { LDAPURI: "ldap://ldap.example.com", START_TLS: false, TLS_CA_FILE: "/ca.pem" });
      fixture.detectChanges();

      expect(component.tlsVersionDisabled()).toBe(true);
      expect(component.tlsVerifyDisabled()).toBe(true);
      expect(component.ldapForm.TLS_CA_FILE().disabled()).toBe(true);
      expect(component.getValue().TLS_CA_FILE).toBe("/ca.pem");
    });

    it("lets the admin choose TLS 1.2 for an ldaps URI", () => {
      componentRef.setInput("data", { LDAPURI: "ldaps://ldap.example.com" });
      fixture.detectChanges();
      component.model.update((m) => ({ ...m, TLS_VERSION: "5" }));

      expect(component.getValue().TLS_VERSION).toBe("5");
    });
  });

  describe("edits through the controls", () => {
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const checkboxInput = (label: string): HTMLInputElement => {
      const checkbox = Array.from(
        fixture.nativeElement.querySelectorAll("mat-checkbox") as NodeListOf<HTMLElement>
      ).find((el) => el.textContent?.includes(label));
      return checkbox!.querySelector("input") as HTMLInputElement;
    };
    const selectByLabel = (label: string): MatSelect =>
      fixture.debugElement
        .queryAll(By.directive(MatSelect))
        .find((d) => d.nativeElement.closest("mat-form-field")?.textContent?.includes(label))!
        .componentInstance as MatSelect;
    const clearButtonOf = (input: HTMLInputElement) =>
      input.closest("app-clearable-input")!.querySelector("button") as HTMLButtonElement;

    beforeEach(async () => {
      componentRef.setInput("data", { LDAPURI: "ldap://ldap.example.com", START_TLS: true, TLS_VERIFY: true });
      await flush();
    });

    it("starts pristine after the data input is applied", () => {
      expect(component.isDirty()).toBe(false);
    });

    it.each([
      ["STARTTLS", "START_TLS", false],
      ["Verify TLS certificate", "TLS_VERIFY", false],
      ["Per-Process Server Pool", "SERVERPOOL_PERSISTENT", true],
      ["Edit User Store", "EDITABLE", true],
      ["Recursive Search of User Groups", "recursive_group_search", true],
      ["No Anonymous Referral Chasing", "NOREFERRALS", true],
      ["No Retrieval of Schema Information", "NOSCHEMAS", true]
    ] as const)("%s writes %s to the model and marks the resolver dirty", async (label, field, expected) => {
      checkboxInput(label).click();
      await flush();

      expect(component.model()[field]).toBe(expected);
      expect(component.ldapForm[field]().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("shows a model change in the checkbox", async () => {
      component.model.update((m) => ({ ...m, NOSCHEMAS: true }));
      await flush();

      expect(checkboxInput("No Retrieval of Schema Information").checked).toBe(true);
      expect(component.isDirty()).toBe(false);
    });

    it.each([
      ["Scope", "SCOPE", "BASE"],
      ["TLS Version", "TLS_VERSION", "5"],
      ["Bind Type", "AUTHTYPE", "Anonymous"]
    ] as const)("the %s select writes %s to the model and marks the resolver dirty", async (label, field, value) => {
      selectByLabel(label)
        .options.find((o) => o.value === value)!
        .select();
      await flush();

      expect(component.model()[field]).toBe(value);
      expect(component.ldapForm[field]().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("marks the resolver dirty when a clear button empties a field", async () => {
      component.model.update((m) => ({ ...m, LDAPBASE: "dc=example,dc=com" }));
      await flush();
      const base = fixture.nativeElement.querySelector("input.mat-mdc-input-element") as HTMLInputElement;
      expect(component.isDirty()).toBe(false);

      clearButtonOf(base).click();
      await flush();

      expect(component.model().LDAPBASE).toBe("");
      expect(component.ldapForm.LDAPBASE().dirty()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("marks the resolver dirty when a preset is applied", () => {
      component.applyLdapPreset(component.ldapPresets[0]);

      expect(component.isDirty()).toBe(true);
    });

    it("disables the STARTTLS checkbox for an ldaps URI through the form", async () => {
      componentRef.setInput("data", { LDAPURI: "ldaps://ldap.example.com" });
      await flush();

      expect(component.ldapForm.START_TLS().disabled()).toBe(true);
      expect(checkboxInput("STARTTLS").disabled).toBe(true);
    });

    it("disables the TLS version and verification without TLS through the form", async () => {
      componentRef.setInput("data", { LDAPURI: "ldap://ldap.example.com", START_TLS: false });
      await flush();

      expect(component.ldapForm.TLS_VERSION().disabled()).toBe(true);
      expect(component.ldapForm.TLS_VERIFY().disabled()).toBe(true);
      expect(checkboxInput("Verify TLS certificate").disabled).toBe(true);
      expect(component.isValid()).toBe(false);
    });
  });

  describe("number fields", () => {
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const numberInput = (index: number): HTMLInputElement =>
      fixture.nativeElement.querySelectorAll("input[type='number']")[index];
    const type = async (input: HTMLInputElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("blur"));
      await flush();
    };
    const filled = {
      LDAPURI: "ldap://ldap.example.com",
      LDAPBASE: "dc=example,dc=com",
      LOGINNAMEATTRIBUTE: "uid",
      LDAPSEARCHFILTER: "(uid=*)",
      USERINFO: "{}"
    };

    beforeEach(async () => {
      componentRef.setInput("data", filled);
      await flush();
    });

    it("is valid with the default numbers", () => {
      expect(component.isValid()).toBe(true);
    });

    it.each([
      [0, "TIMEOUT"],
      [1, "CACHE_TIMEOUT"],
      [2, "SIZELIMIT"],
      [3, "SERVERPOOL_ROUNDS"],
      [4, "SERVERPOOL_SKIP"]
    ] as const)("number input %s (%s) is required and shows the message once emptied", async (index, field) => {
      await type(numberInput(index), "");

      expect(component.model()[field]).toBeNull();
      expect(
        component.ldapForm[field]()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      expect(component.isValid()).toBe(false);
      const field_ = numberInput(index).closest("mat-form-field")!;
      expect(field_.querySelector("mat-error")?.textContent).toContain("required");
    });

    it("stores a typed number as a number", async () => {
      await type(numberInput(0), "12");

      expect(component.model().TIMEOUT).toBe(12);
      expect(component.isValid()).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("keeps the model and shows a parse message for text the browser cannot parse", async () => {
      jest.spyOn(numberInput(0), "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
      await type(numberInput(0), "");

      expect(component.model().TIMEOUT).toBe(5);
      expect(
        component.ldapForm
          .TIMEOUT()
          .errors()
          .map((e) => e.kind)
      ).toContain("parse");
      expect(component.isValid()).toBe(false);
      const messages = Array.from(numberInput(0).closest("mat-form-field")!.querySelectorAll("mat-error")).map(
        (e) => e.textContent
      );
      expect(messages.join(" ")).toContain("number");
    });
  });
});
