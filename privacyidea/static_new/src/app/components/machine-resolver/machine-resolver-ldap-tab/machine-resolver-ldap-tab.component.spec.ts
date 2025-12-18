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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MachineResolverLdapTabComponent } from "./machine-resolver-ldap-tab.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { LdapMachineResolverData } from "../../../services/machine-resolver/machine-resolver.service";

describe("MachineResolverLdapTabComponent", () => {
  let component: MachineResolverLdapTabComponent;
  let fixture: ComponentFixture<MachineResolverLdapTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverLdapTabComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverLdapTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("isEditMode", false);
    fixture.componentRef.setInput("machineResolverData", { type: "ldap", resolver: "test" } as LdapMachineResolverData);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should check validity", () => {
    const validData: LdapMachineResolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      LDAPBASE: "dc=test",
      BINDDN: "cn=admin",
      BINDPW: "password",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: "False",
      resolver: ""
    };
    const invalidData1 = { type: "hosts" };
    const invalidData2: LdapMachineResolverData = { ...validData, LDAPURI: " " };
    const invalidData3: LdapMachineResolverData = { ...validData, LDAPBASE: " " };
    const invalidData4: LdapMachineResolverData = { ...validData, BINDDN: " " };
    const invalidData5: LdapMachineResolverData = { ...validData, BINDPW: " " };

    expect(component.isValid(validData)).toBeTruthy();
    expect(component.isValid(invalidData1 as any)).toBeFalsy();
    expect(component.isValid(invalidData2)).toBeFalsy();
    expect(component.isValid(invalidData3)).toBeFalsy();
    expect(component.isValid(invalidData4)).toBeFalsy();
    expect(component.isValid(invalidData5)).toBeFalsy();
  });

  it("should update data with patch only", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: LdapMachineResolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      LDAPBASE: "dc=test",
      BINDDN: "cn=admin",
      BINDPW: "password",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: "False",
      resolver: ""
    };
    fixture.componentRef.setInput("machineResolverData", initialData);
    const patch = { LDAPURI: "ldap://updated" };
    component.updateData(patch);
    expect(component.onNewData.emit).toHaveBeenCalledWith({ ...initialData, ...patch, type: "ldap" });
  });

  it("should update data with patch and remove", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: LdapMachineResolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      LDAPBASE: "dc=test",
      BINDDN: "cn=admin",
      BINDPW: "password",
      resolver: "name",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: false
    };
    fixture.componentRef.setInput("machineResolverData", initialData);
    const patch = { LDAPURI: "ldap://updated", LDAPBASE: "dc=updated", BINDDN: "cn=updated", BINDPW: "updated" };
    component.updateData({ patch, remove: ["resolver", "AUTHTYPE"] });
    const expectedData: Partial<LdapMachineResolverData> = {
      type: "ldap",
      LDAPURI: "ldap://updated",
      LDAPBASE: "dc=updated",
      BINDDN: "cn=updated",
      BINDPW: "updated",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: false
    };
    expect(component.onNewData.emit).toHaveBeenCalledWith(expectedData);
  });

  it("should update data with remove only", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: LdapMachineResolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      LDAPBASE: "dc=test",
      BINDDN: "cn=admin",
      BINDPW: "password",
      resolver: "name",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: false
    };
    fixture.componentRef.setInput("machineResolverData", initialData);
    component.updateData({
      remove: [
        "resolver",
        "AUTHTYPE",
        "TIMEOUT",
        "SIZELIMIT",
        "SEARCHFILTER",
        "IDATTRIBUTE",
        "IPATTRIBUTE",
        "HOSTNAMEATTRIBUTE",
        "NOREFERRALS",
        "START_TLS",
        "TLS_CA_FILE"
      ]
    });
    const expectedData: Partial<LdapMachineResolverData> = {
      type: "ldap",
      LDAPURI: "ldap://test",
      LDAPBASE: "dc=test",
      BINDDN: "cn=admin",
      BINDPW: "password",
      TLS_VERIFY: false
    };
    expect(component.onNewData.emit).toHaveBeenCalledWith(expectedData);
  });

  it("should update tls verify", () => {
    jest.spyOn(component, "updateData");
    component.updateTlsVerify(true);
    expect(component.updateData).toHaveBeenCalledWith({
      patch: { TLS_VERIFY: true, TLS_CA_FILE: undefined },
      remove: ["TLS_CA_FILE"]
    });
  });
});
