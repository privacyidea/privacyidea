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
import { ConditionsUserComponent } from "./conditions-user.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { Realm, Realms, RealmService } from "../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../services/resolver/resolver.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockHttpResourceRef, MockPiResponse, MockRealmService } from "../../../../../../testing/mock-services";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

import { MockResolverService } from "../../../../../../testing/mock-services/mock-resolver-service";

describe("ConditionsUserComponent", () => {
  let component: ConditionsUserComponent;
  let fixture: ComponentFixture<ConditionsUserComponent>;
  let policyServiceMock: MockPolicyService;
  let realmServiceMock: MockRealmService;
  let resolverServiceMock: MockResolverService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionsUserComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionsUserComponent);
    component = fixture.componentInstance;
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    realmServiceMock = TestBed.inject(RealmService) as unknown as MockRealmService;
    resolverServiceMock = TestBed.inject(ResolverService) as unknown as MockResolverService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should select realms", () => {
    component.selectRealm(["realm1"]);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: ["realm1"] });
  });

  it("should toggle all realms", () => {
    const ref = realmServiceMock.realmResource as unknown as MockHttpResourceRef<MockPiResponse<Realms> | undefined>;
    ref.set(
      MockPiResponse.fromValue<Realms>({
        realm1: { default: false, id: 1, option: "", resolver: [] } as Realm,
        realm2: { default: false, id: 2, option: "", resolver: [] } as Realm
      } as any)
    );

    component.toggleAllRealms();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: ["realm1", "realm2"] });

    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, realm: ["realm1", "realm2"] });
    fixture.detectChanges();
    component.toggleAllRealms();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ realm: [] });
  });

  it("should select resolvers", () => {
    component.selectResolver(["resolver1"]);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: ["resolver1"] });
  });

  it("should toggle all resolvers", () => {
    resolverServiceMock.setResolverOptions(["resolver1", "resolver2"]);
    component.toggleAllResolvers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: ["resolver1", "resolver2"] });

    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, resolver: ["resolver1", "resolver2"] });
    fixture.detectChanges();
    component.toggleAllResolvers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ resolver: [] });
  });

  it("should add user", () => {
    component.userFormControl.setValue("testuser");
    component.addUser("testuser");
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: ["testuser"] });
  });

  it("should remove user", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, user: ["testuser"] });
    fixture.detectChanges();
    component.removeUser("testuser");
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: [] });
  });

  it("should clear users", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, user: ["testuser"] });
    fixture.detectChanges();
    component.clearUsers();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user: [] });
  });

  it("should toggle user case insensitive", () => {
    component.toggleUserCaseInsensitive();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user_case_insensitive: true });
  });

  it("should validate user", () => {
    expect(component.userValidator(component.userFormControl)).toBeNull();
    component.userFormControl.setValue("invalid,");
    expect(component.userValidator(component.userFormControl)).toEqual({ includesComma: { value: "invalid," } });
  });
});
