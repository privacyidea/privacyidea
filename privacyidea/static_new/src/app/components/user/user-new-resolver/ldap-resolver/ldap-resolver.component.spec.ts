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
import { LdapResolverComponent } from "./ldap-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";
import { ResolverService } from "../../../../services/resolver/resolver.service";
import { MockResolverService } from "../../../../../testing/mock-services/mock-resolver-service";

describe("LdapResolverComponent", () => {
  let component: LdapResolverComponent;
  let componentRef: ComponentRef<LdapResolverComponent>;
  let fixture: ComponentFixture<LdapResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LdapResolverComponent, NoopAnimationsModule],
      providers: [
        { provide: ResolverService, useClass: MockResolverService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(LdapResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose controls via signal", () => {
    const controls = component.controls();
    expect(controls).toEqual(expect.objectContaining({
      LDAPURI: component.ldapUriControl,
      LDAPBASE: component.ldapBaseControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      LDAPURI: "ldap://localhost",
      LDAPBASE: "dc=example,dc=com",
      LOGINNAMEATTRIBUTE: "uid",
      LDAPSEARCHFILTER: "(objectClass=*)",
      USERINFO: "description"
    });

    fixture.detectChanges();

    expect(component.ldapUriControl.value).toBe("ldap://localhost");
    expect(component.ldapBaseControl.value).toBe("dc=example,dc=com");
    expect(component.loginNameAttributeControl.value).toBe("uid");
    expect(component.ldapSearchFilterControl.value).toBe("(objectClass=*)");
    expect(component.userInfoControl.value).toBe("description");
  });

  it("should parse boolean and numeric strings from data input", () => {
    componentRef.setInput("data", {
      recursive_group_search: "False",
      TLS_VERIFY: "True",
      TIMEOUT: "5",
      EDITABLE: "False"
    });

    fixture.detectChanges();

    expect(component.recursiveGroupSearchControl.value).toBe(false);
    expect(component.tlsVerifyControl.value).toBe(true);
    expect(component.timeoutControl.value).toBe(5);
    expect(component.editableControl.value).toBe(false);
  });

  it("should parse '1' and '0' strings as booleans from data input", () => {
    componentRef.setInput("data", {
      recursive_group_search: "1",
      TLS_VERIFY: "0",
      EDITABLE: "1"
    });

    fixture.detectChanges();

    expect(component.recursiveGroupSearchControl.value).toBe(true);
    expect(component.tlsVerifyControl.value).toBe(false);
    expect(component.editableControl.value).toBe(true);
  });

  it("should apply LDAP presets", () => {
    const preset = component.ldapPresets[0];
    component.applyLdapPreset(preset);
    expect(component.loginNameAttributeControl.value).toBe(preset.loginName);
    expect(component.ldapSearchFilterControl.value).toBe(preset.searchFilter);
    expect(component.userInfoControl.value).toBe(preset.userInfo);
    expect(component.uidTypeControl.value).toBe(preset.uidType);
    expect(component.multivalueAttributesControl.value).toBe("");
  });
});
