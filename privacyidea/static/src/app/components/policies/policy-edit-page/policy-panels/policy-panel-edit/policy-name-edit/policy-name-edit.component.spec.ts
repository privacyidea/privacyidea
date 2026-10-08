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
import { PolicyNameEditComponent } from "./policy-name-edit.component";

describe("PolicyNameEditComponent", () => {
  let component: PolicyNameEditComponent;
  let fixture: ComponentFixture<PolicyNameEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyNameEditComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyNameEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policyName", "Test Policy");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update the model when policyName is changed", () => {
    const spy = jest.spyOn(component.policyName, "set");
    component.policyName.set("New Name");
    expect(spy).toHaveBeenCalledWith("New Name");
  });

  describe("name collision", () => {
    const errorKinds = () =>
      component
        .nameField()
        .errors()
        .map((e) => e.kind);

    beforeEach(() => {
      fixture.componentRef.setInput("policyName", "helpdesk");
      fixture.detectChanges();
    });

    it("should report no collision by default", () => {
      expect(errorKinds()).not.toContain("nameTaken");
      expect(component.nameField().valid()).toBe(true);
    });

    it("should flag the name as invalid while the parent reports it as taken", () => {
      fixture.componentRef.setInput("nameTaken", true);
      fixture.detectChanges();

      expect(errorKinds()).toContain("nameTaken");
      expect(component.nameField().valid()).toBe(false);
    });

    it("should show the error message of the collision at once, without the field having been focused", () => {
      expect(component.nameField().touched()).toBe(false);

      fixture.componentRef.setInput("nameTaken", true);
      fixture.detectChanges();

      expect(component.nameField().touched()).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain(
        "A policy with this name already exists."
      );
    });

    it("should leave the field untouched while the name is free", () => {
      fixture.detectChanges();

      expect(component.nameField().touched()).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
    });

    it("should hide the error message again once the name is free", () => {
      fixture.componentRef.setInput("nameTaken", true);
      fixture.detectChanges();
      fixture.componentRef.setInput("nameTaken", false);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
    });

    it("should clear the error once the parent no longer reports a collision", () => {
      fixture.componentRef.setInput("nameTaken", true);
      fixture.detectChanges();
      fixture.componentRef.setInput("nameTaken", false);
      fixture.detectChanges();

      expect(errorKinds()).not.toContain("nameTaken");
      expect(component.nameField().valid()).toBe(true);
    });

    it("should report the collision next to the other validation errors", () => {
      fixture.componentRef.setInput("nameTaken", true);
      component.policyName.set("invalid name");
      fixture.detectChanges();

      expect(errorKinds()).toEqual(expect.arrayContaining(["pattern", "nameTaken"]));
    });
  });
});
