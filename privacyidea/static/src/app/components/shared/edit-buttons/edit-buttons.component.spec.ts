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

import { signal } from "@angular/core";
import { EditableElement, EditButtonsComponent } from "./edit-buttons.component";

describe("EditButtonsComponent", () => {
  let component: EditButtonsComponent<EditableElement>;
  let fixture: ComponentFixture<EditButtonsComponent<EditableElement>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditButtonsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(EditButtonsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("element", {
      keyMap: { key: "value", label: "label" },
      isEditing: signal(false)
    });
    fixture.componentRef.setInput("isEditingUser", false);
    fixture.componentRef.setInput("isEditingInfo", false);
    fixture.componentRef.setInput("shouldHideEdit", false);
    fixture.componentRef.setInput("toggleEdit", jest.fn());
    fixture.componentRef.setInput("saveEdit", jest.fn());
    fixture.componentRef.setInput("cancelEdit", jest.fn());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
