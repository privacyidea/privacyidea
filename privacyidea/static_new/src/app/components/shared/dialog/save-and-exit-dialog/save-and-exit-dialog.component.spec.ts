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
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";
import { SaveAndExitDialogComponent, SaveAndExitDialogData } from "./save-and-exit-dialog.component";

describe("SaveAndExitDialogComponent", () => {
  let component: SaveAndExitDialogComponent;
  let fixture: ComponentFixture<SaveAndExitDialogComponent>;
  let mockDialogRef: MockMatDialogRef<any, any>;

  beforeEach(async () => {
    const mockValue: SaveAndExitDialogData = {
      title: "Unsaved Changes",
      message: "Do you want to save before leaving?",
      allowSaveExit: true,
      saveExitDisabled: false,
      saveButtonText: "save button text",
      discardButtonText: "discard button text"
    };

    await TestBed.configureTestingModule({
      imports: [SaveAndExitDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: mockValue
        },
        {
          provide: MatDialogRef,
          useClass: MockMatDialogRef
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SaveAndExitDialogComponent);
    component = fixture.componentInstance;
    mockDialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any, any>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("Actions Logic", () => {
    it("should compute both actions when save is allowed", () => {
      const actions = component.actions();
      expect(actions.length).toBe(2);
      expect(actions.some((a) => a.value === "save-exit")).toBeTruthy();
      expect(actions.some((a) => a.value === "discard")).toBeTruthy();
    });
  });

  describe("Interactions", () => {
    it("should close with 'discard' on discard action", () => {
      const spy = jest.spyOn(mockDialogRef, "close");
      component.onAction("discard");
      expect(spy).toHaveBeenCalledWith("discard");
    });

    it("should close with 'save-exit' on save action", () => {
      const spy = jest.spyOn(mockDialogRef, "close");
      component.onAction("save-exit");
      expect(spy).toHaveBeenCalledWith("save-exit");
    });
  });
});
