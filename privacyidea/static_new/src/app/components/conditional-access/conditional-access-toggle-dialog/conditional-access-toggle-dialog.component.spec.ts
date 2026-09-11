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
  ConditionalAccessToggleDialogComponent,
  ConditionalAccessToggleDialogData
} from "./conditional-access-toggle-dialog.component";

describe("ConditionalAccessToggleDialogComponent", () => {
  let component: ConditionalAccessToggleDialogComponent;
  let fixture: ComponentFixture<ConditionalAccessToggleDialogComponent>;
  let dialogRef: MockMatDialogRef<unknown, unknown>;

  const data: ConditionalAccessToggleDialogData = {
    title: "Toggle policies",
    intro: "The following policies will change:",
    onWord: "enabled",
    offWord: "disabled",
    items: [
      { label: "Policy A", state: true },
      { label: "Policy B", state: false }
    ]
  };

  beforeEach(async () => {
    dialogRef = new MockMatDialogRef<unknown, unknown>();
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessToggleDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessToggleDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders the state-transition word for each item (both directions)", () => {
    const text = (fixture.nativeElement as HTMLElement).textContent ?? "";
    // enabled item -> on-to-off transition; disabled item -> off-to-on transition.
    expect(component.onToOff).toBe("enabled → disabled");
    expect(component.offToOn).toBe("disabled → enabled");
    expect(text).toContain("Policy A (enabled → disabled)");
    expect(text).toContain("Policy B (disabled → enabled)");
  });

  it("exposes activate/deactivate/toggle actions", () => {
    expect(component.actions.map((a) => a.value)).toEqual(["activate", "deactivate", "toggle"]);
  });

  it("closes with the chosen action value", () => {
    component.onAction("toggle");
    expect(dialogRef.close).toHaveBeenCalledWith("toggle");
  });
});
