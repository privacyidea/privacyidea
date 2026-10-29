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
import { RealmService } from "@services/realm/realm.service";
import { MockRealmService } from "@testing/mock-services";
import { EditUserConditionsComponent } from "./edit-user-conditions.component";

describe("EditUserConditionsComponent", () => {
  let component: EditUserConditionsComponent;
  let fixture: ComponentFixture<EditUserConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditUserConditionsComponent],
      providers: [{ provide: RealmService, useClass: MockRealmService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EditUserConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      user: ["testuser"],
      realm: ["realm1"],
      resolver: ["resolver1"],
      user_case_insensitive: false
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit edits when selecting realms", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.selectRealm(["realm2"]);
    expect(spy).toHaveBeenCalledWith({ realm: ["realm2"] });
  });

  it("should add user and clear form", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addUser("newuser");
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        user: ["testuser", "newuser"]
      })
    );
  });

  it("should toggle user case insensitive state", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.toggleUserCaseInsensitive();
    expect(spy).toHaveBeenCalledWith({ user_case_insensitive: true });
  });

  describe("available resolvers", () => {
    const realmWith = (id: number, ...names: string[]) => ({
      default: false,
      id,
      option: "",
      resolver: names.map((name) => ({ name, node: "", type: "passwdresolver", priority: null }))
    });

    beforeEach(() => {
      const realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
      realmService.realms.set({
        realm1: realmWith(1, "resolver1", "resolver2"),
        realm2: realmWith(2, "resolver2", "resolver3")
      });
    });

    it("should offer the resolvers of every realm while no realm is selected", () => {
      fixture.componentRef.setInput("policy", { realm: [], resolver: [] });
      expect(component.availableResolvers().sort()).toEqual(["resolver1", "resolver2", "resolver3"]);
      expect(component.selectResolverHint()).toBe(
        "Lists the resolvers of all realms. A resolver that is in no realm is not listed."
      );
    });

    it("should offer the resolvers of the selected realms", () => {
      fixture.componentRef.setInput("policy", { realm: ["realm2"], resolver: [] });
      expect(component.availableResolvers().sort()).toEqual(["resolver2", "resolver3"]);
      expect(component.selectResolverHint()).toBe("Lists the resolvers of the selected realms.");
    });
  });

  describe("check all resolvers", () => {
    const checkbox = (): HTMLInputElement =>
      fixture.nativeElement.querySelector(".check-all-resolvers input[type='checkbox']");
    const description = (): HTMLElement => fixture.nativeElement.querySelector("#check-all-resolvers-description");
    const setPolicy = (resolver: string[], check_all_resolvers: boolean) => {
      fixture.componentRef.setInput("policy", { realm: ["realm1"], resolver, check_all_resolvers });
      fixture.detectChanges();
    };

    it("should toggle the option", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.toggleCheckAllResolvers();
      expect(spy).toHaveBeenCalledWith({ check_all_resolvers: true });
    });

    it("should keep the option when the last resolver is removed", () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      component.selectResolver([]);
      expect(spy).toHaveBeenCalledWith({ resolver: [] });
    });

    it("should enable the checkbox and explain the option while resolvers are selected", () => {
      setPolicy(["resolver1"], true);
      expect(checkbox().checked).toBe(true);
      expect(checkbox().disabled).toBe(false);
      expect(checkbox().getAttribute("aria-describedby")).toContain("check-all-resolvers-description");
      expect(description().classList).toContain("checkbox-hint");
      expect(description().textContent!.trim()).toBe(
        "Also match users who are contained in one of the selected resolvers, but were found in another resolver of the realm."
      );
    });

    it("should disable the unchecked checkbox without resolvers", () => {
      setPolicy([], false);
      expect(checkbox().checked).toBe(false);
      expect(checkbox().disabled).toBe(true);
      expect(description().classList).toContain("checkbox-hint");
      expect(description().textContent!.trim()).toBe("Select a resolver to use this option.");
    });

    it("should warn and let the option be cleared while it is set without resolvers", () => {
      setPolicy([], true);
      expect(checkbox().checked).toBe(true);
      expect(checkbox().disabled).toBe(false);
      expect(description().classList).toContain("checkbox-error");
      expect(description().textContent!.trim()).toBe(
        "Without a resolver, a policy with this option matches no user. Select a resolver or clear this option."
      );
    });
  });

  it("should validate that user does not contain commas", () => {
    component.userSignal.set("user,name");
    expect(component.userField().valid()).toBe(false);
    expect(
      component
        .userField()
        .errors()
        .some((e) => e.kind === "includesComma")
    ).toBe(true);
  });
});
