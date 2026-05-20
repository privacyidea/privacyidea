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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  ToggleActiveDialogComponent,
  ToggleActiveDialogData
} from "./toggle-active-dialog.component";

describe("ToggleActiveDialogComponent", () => {
  let component: ToggleActiveDialogComponent;
  let fixture: ComponentFixture<ToggleActiveDialogComponent>;
  let mockDialogRef: MockMatDialogRef<ToggleActiveDialogComponent>;

  const mockData: ToggleActiveDialogData = {
    items: [
      { serial: "TOK001", active: true },
      { serial: "TOK002", active: false },
      { serial: "TOK003", active: true }
    ]
  };

  beforeEach(async () => {
    mockDialogRef = new MockMatDialogRef();

    await TestBed.configureTestingModule({
      imports: [ToggleActiveDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: MatDialogRef, useValue: mockDialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ToggleActiveDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have three actions: Activate All, Deactivate All, Toggle All", () => {
    expect(component.actions).toHaveLength(3);
    expect(component.actions.map((a) => a.value)).toEqual(["activate", "deactivate", "toggle"]);
  });

  it("should have Toggle All as the primary action", () => {
    const toggleAction = component.actions.find((a) => a.value === "toggle");
    expect(toggleAction?.primary).toBe(true);
  });

  it("should have Activate All and Deactivate All as non-primary", () => {
    const activateAction = component.actions.find((a) => a.value === "activate");
    const deactivateAction = component.actions.find((a) => a.value === "deactivate");
    expect(activateAction?.primary).toBe(false);
    expect(deactivateAction?.primary).toBe(false);
  });

  it("should close with 'toggle' when onAction is called with 'toggle'", () => {
    component.onAction("toggle");
    expect(mockDialogRef.close).toHaveBeenCalledWith("toggle");
  });

  it("should close with 'activate' when onAction is called with 'activate'", () => {
    component.onAction("activate");
    expect(mockDialogRef.close).toHaveBeenCalledWith("activate");
  });

  it("should close with 'deactivate' when onAction is called with 'deactivate'", () => {
    component.onAction("deactivate");
    expect(mockDialogRef.close).toHaveBeenCalledWith("deactivate");
  });

  it("should close without result when close is called", () => {
    component["close"]();
    expect(mockDialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it("should display all token items in the template", () => {
    const listItems = fixture.nativeElement.querySelectorAll("li");
    expect(listItems).toHaveLength(3);
    expect(listItems[0].textContent).toContain("TOK001");
    expect(listItems[0].textContent).toContain("active → inactive");
    expect(listItems[1].textContent).toContain("TOK002");
    expect(listItems[1].textContent).toContain("inactive → active");
    expect(listItems[2].textContent).toContain("TOK003");
    expect(listItems[2].textContent).toContain("active → inactive");
  });
});

