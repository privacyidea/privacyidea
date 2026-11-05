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
import { By } from "@angular/platform-browser";
import { PolicyDescriptionEditComponent } from "./policy-description-edit.component";

describe("PolicyDescriptionEditComponent", () => {
  let component: PolicyDescriptionEditComponent;
  let fixture: ComponentFixture<PolicyDescriptionEditComponent>;

  const textarea = (): HTMLTextAreaElement => fixture.debugElement.query(By.css("textarea")).nativeElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyDescriptionEditComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyDescriptionEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("description", "Initial description");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show the description in the textarea", () => {
    expect(textarea().value).toBe("Initial description");
  });

  it("should show a description that the parent changes", async () => {
    fixture.componentRef.setInput("description", "Changed by the parent");
    fixture.detectChanges();
    await fixture.whenStable();

    expect(textarea().value).toBe("Changed by the parent");
  });

  it("should emit descriptionChange and mark the field dirty when the user types", () => {
    const emitted: string[] = [];
    component.description.subscribe((value) => emitted.push(value));
    expect(component.descriptionField().dirty()).toBe(false);

    textarea().value = "Updated description";
    textarea().dispatchEvent(new Event("input"));

    expect(emitted).toEqual(["Updated description"]);
    expect(component.description()).toBe("Updated description");
    expect(component.descriptionField().dirty()).toBe(true);
  });

  it("should emit an empty description when the user clears the textarea", () => {
    textarea().value = "";
    textarea().dispatchEvent(new Event("input"));

    expect(component.description()).toBe("");
  });
});
