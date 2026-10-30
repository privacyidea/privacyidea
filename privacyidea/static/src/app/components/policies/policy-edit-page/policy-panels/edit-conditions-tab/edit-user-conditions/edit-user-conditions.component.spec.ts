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
import { PolicyService } from "@services/policies/policies.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockRealmService } from "@testing/mock-services";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { EditUserConditionsComponent } from "./edit-user-conditions.component";

describe("EditUserConditionsComponent", () => {
  let component: EditUserConditionsComponent;
  let fixture: ComponentFixture<EditUserConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditUserConditionsComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
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
    (fixture.nativeElement as HTMLElement).querySelectorAll(".chip-list-extras button, mat-checkbox");

  it("should show the users as chips", () => {
    const chips = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll(".mat-mdc-chip-action-label"));
    expect(chips.map((chip) => chip.textContent!.trim())).toEqual(["testuser"]);
  });

  it("should emit only the users when an entry is added", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    chipList().triggerEventHandler("valuesChange", ["testuser", "newuser"]);
    expect(spy).toHaveBeenCalledWith({ user: ["testuser", "newuser"] });
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
    const checkbox = () => fixture.debugElement.query(By.directive(MatCheckbox)).componentInstance as MatCheckbox;
    const checkboxInput = (): HTMLInputElement =>
      fixture.debugElement.query(By.css("mat-checkbox input")).nativeElement;
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
