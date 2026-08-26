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
import { BlocklistBlockDialogComponent, BlocklistBlockDialogResult } from "./blocklist-block-dialog.component";

describe("BlocklistBlockDialogComponent", () => {
  let component: BlocklistBlockDialogComponent;
  let fixture: ComponentFixture<BlocklistBlockDialogComponent>;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<BlocklistBlockDialogComponent, BlocklistBlockDialogResult | null>>;

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [BlocklistBlockDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: undefined }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(BlocklistBlockDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("cannot be confirmed without an address", () => {
    expect(component.canConfirm()).toBe(false);
    component.ip.set("  ");
    expect(component.canConfirm()).toBe(false);
    component.ip.set("203.0.113.9");
    expect(component.canConfirm()).toBe(true);
  });

  it("closes with a trimmed address and a null duration for a permanent block", () => {
    component.ip.set(" 203.0.113.9 ");
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: null });
  });

  it("converts the entered duration to seconds using the selected unit", () => {
    component.ip.set("203.0.113.9");
    component.mode.set("timed");
    component.durationInput.set("2");
    component.durationUnit.set("hours");
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: 7200 });
  });

  it("does not close while a timed block has no valid duration", () => {
    component.ip.set("203.0.113.9");
    component.mode.set("timed");
    component.onAction("confirm");
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });
});
