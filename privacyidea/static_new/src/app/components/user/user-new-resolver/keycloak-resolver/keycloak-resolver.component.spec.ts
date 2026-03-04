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
import { KeycloakResolverComponent } from "./keycloak-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { ResolverService } from "../../../../services/resolver/resolver.service";
import { MockResolverService } from "../../../../../testing/mock-services/mock-resolver-service";

describe("KeycloakResolverComponent", () => {
  let component: KeycloakResolverComponent;
  let componentRef: ComponentRef<KeycloakResolverComponent>;
  let fixture: ComponentFixture<KeycloakResolverComponent>;
  let resolverService: MockResolverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService }
      ],
      imports: [KeycloakResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    fixture = TestBed.createComponent(KeycloakResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize default data on creation", () => {
    const defaultData = {
      base_url: "http://localhost:8080",
      config_authorization: { endpoint: "/realms/{realm}/protocol/openid-connect/token" }
    };
    componentRef.setInput("data", defaultData);
    fixture.detectChanges();
    expect(component.baseUrlControl.value).toBe("http://localhost:8080");
    expect(component.configAuthorizationGroup.value.endpoint).toBe("/realms/{realm}/protocol/openid-connect/token");
  });

  it("should enable group fields when active is true in data", () => {
    const data = {
      config_get_user_groups: {
        active: true,
        user_groups_attribute: "name",
        endpoint: "/groups",
        method: "GET"
      }
    };
    componentRef.setInput("data", data);
    fixture.detectChanges();

    expect(component.userGroupsControl.get("active")?.value).toBe(true);
    expect(component.userGroupsControl.get("user_groups_attribute")?.enabled).toBe(true);
    expect(component.userGroupsControl.get("endpoint")?.enabled).toBe(true);
    expect(component.userGroupsControl.get("method")?.enabled).toBe(true);
    // Programmatic updates should NOT mark the form as dirty
    expect(component.userGroupsControl.dirty).toBe(false);
  });

  it("should disable group fields when active is false in data", () => {
    const data = {
      config_get_user_groups: {
        active: false,
        user_groups_attribute: "name"
      }
    };
    componentRef.setInput("data", data);
    fixture.detectChanges();

    expect(component.userGroupsControl.get("active")?.value).toBe(false);
    expect(component.userGroupsControl.get("user_groups_attribute")?.disabled).toBe(true);
  });
});
