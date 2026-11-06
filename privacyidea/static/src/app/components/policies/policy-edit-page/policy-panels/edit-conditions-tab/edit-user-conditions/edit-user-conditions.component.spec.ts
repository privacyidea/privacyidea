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
import { MatCheckbox } from "@angular/material/checkbox";
import { By } from "@angular/platform-browser";
import { ChipListInputComponent } from "@components/shared/chip-list-input/chip-list-input.component";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockRealmService } from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { EditUserConditionsComponent } from "./edit-user-conditions.component";

describe("EditUserConditionsComponent", () => {
  let component: EditUserConditionsComponent;
  let fixture: ComponentFixture<EditUserConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditUserConditionsComponent],
      providers: [
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
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

  const chipList = () => fixture.debugElement.query(By.directive(ChipListInputComponent));
  const extras = () =>
    (fixture.nativeElement as HTMLElement).querySelectorAll(".chip-list-extras button, .chip-list-extras mat-checkbox");

  it("should show the users as chips", () => {
    const chips = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll(".mat-mdc-chip-action-label"));
    expect(chips.map((chip) => chip.textContent!.trim())).toEqual(["testuser"]);
  });

  it("should emit only the users when an entry is added", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    chipList().triggerEventHandler("valuesChange", ["testuser", "newuser"]);
    expect(spy).toHaveBeenCalledWith({ user: ["testuser", "newuser"] });
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

    it("should offer every resolver while no realm is selected", () => {
      const resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
      resolverService.setResolverOptions(["resolver1", "resolver2", "resolver3", "unused"]);
      fixture.componentRef.setInput("policy", { realm: [], resolver: [] });
      expect(component.availableResolvers().sort()).toEqual(["resolver1", "resolver2", "resolver3", "unused"]);
      expect(component.selectResolverHint()).toBe("Lists all resolvers.");
    });

    it("should offer the resolvers of every realm while no realm is selected and the resolvers are not listed", () => {
      fixture.componentRef.setInput("policy", { realm: [], resolver: [] });
      expect(component.availableResolvers().sort()).toEqual(["resolver1", "resolver2", "resolver3"]);
      expect(component.selectResolverHint()).toBe(
        "Lists the resolvers of all realms. A resolver that is in no realm is not listed."
      );
    });

    it("should offer the resolvers of the selected realms", () => {
      const resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
      resolverService.setResolverOptions(["resolver1", "resolver2", "resolver3", "unused"]);
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

  it("should emit only the users when an entry is removed", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    chipList().triggerEventHandler("valuesChange", []);
    expect(spy).toHaveBeenCalledWith({ user: [] });
  });

  it("should project the case checkbox and the clear button while users exist", () => {
    expect(extras()).toHaveLength(2);
  });

  it("should hide the extras without any user", () => {
    fixture.componentRef.setInput("policy", { user: [], realm: [], resolver: [] });
    fixture.detectChanges();
    expect(extras()).toHaveLength(0);
  });

  it("should clear the users", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.clearUsers();
    expect(spy).toHaveBeenCalledWith({ user: [] });
  });

  describe("case insensitive checkbox", () => {
    const caseCheckbox = () => fixture.debugElement.query(By.css(".chip-list-extras mat-checkbox"));
    const checkbox = () => caseCheckbox().injector.get(MatCheckbox);
    const checkboxInput = (): HTMLInputElement => caseCheckbox().query(By.css("input")).nativeElement;
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    it("should show the state of the policy", async () => {
      expect(checkbox().checked).toBe(false);

      fixture.componentRef.setInput("policy", { user: ["testuser"], user_case_insensitive: true });
      await flush();

      expect(checkbox().checked).toBe(true);
    });

    it("should emit the edit and mark the field dirty when the checkbox is clicked", async () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      expect(component.caseInsensitiveField().dirty()).toBe(false);

      checkboxInput().click();
      await flush();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith({ user_case_insensitive: true });
      expect(component.caseInsensitiveField().dirty()).toBe(true);
    });

    it("should emit false when a checked checkbox is clicked", async () => {
      fixture.componentRef.setInput("policy", { user: ["testuser"], user_case_insensitive: true });
      await flush();
      const spy = jest.spyOn(component.policyEdit, "emit");

      checkboxInput().click();
      await flush();

      expect(spy).toHaveBeenCalledWith({ user_case_insensitive: false });
    });

    it("should not emit an edit while the policy only changes the state", async () => {
      const spy = jest.spyOn(component.policyEdit, "emit");

      fixture.componentRef.setInput("policy", { user: ["testuser"], user_case_insensitive: true });
      await flush();

      expect(spy).not.toHaveBeenCalled();
    });
  });
});
