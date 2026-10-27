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
import { FreeTierDialogComponent } from "./free-tier-dialog.component";

describe("FreeTierDialogComponent", () => {
  let fixture: ComponentFixture<FreeTierDialogComponent>;
  let dialogRefMock: { close: jest.Mock };

  const buttons = (): HTMLElement[] => Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));

  beforeEach(() => {
    dialogRefMock = { close: jest.fn() };

    TestBed.configureTestingModule({
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: null }
      ]
    });

    fixture = TestBed.createComponent(FreeTierDialogComponent);
    fixture.detectChanges();
  });

  it("shows the free tier warning under the enterprise heading", () => {
    expect(fixture.nativeElement.querySelector(".pi-dialog-header").textContent.trim()).toBe(
      "The added value of privacyIDEA Enterprise Edition"
    );
    expect(fixture.nativeElement.textContent).toContain("You are using privacyIDEA with more than 50 users.");
  });

  it("closes with its single okay button", () => {
    expect(buttons()).toHaveLength(1);
    expect(buttons()[0].textContent).toContain("Okay");

    buttons()[0].click();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });
});
