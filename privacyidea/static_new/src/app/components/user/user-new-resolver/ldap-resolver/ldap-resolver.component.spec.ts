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

  it("should apply LDAP presets", () => {
    const preset = component.ldapPresets[0];
    component.applyLdapPreset(preset);
    expect(component.model().LOGINNAMEATTRIBUTE).toBe(preset.loginName);
    expect(component.model().LDAPSEARCHFILTER).toBe(preset.searchFilter);
    expect(component.model().USERINFO).toBe(preset.userInfo);
    expect(component.model().UIDTYPE).toBe(preset.uidType);
    expect(component.model().MULTIVALUEATTRIBUTES).toBe("");
  });
});
