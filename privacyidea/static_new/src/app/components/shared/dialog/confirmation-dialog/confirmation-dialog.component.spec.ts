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

import { SimpleConfirmationDialogComponent, SimpleConfirmationDialogData } from "./confirmation-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";

describe("ConfirmationDialogComponent", () => {
  let component: SimpleConfirmationDialogComponent;
  let fixture: ComponentFixture<SimpleConfirmationDialogComponent>;

  beforeEach(async () => {
    const mockValue: SimpleConfirmationDialogData = {
      title: "Confirm Deletion",
      confirmAction: {
        type: "destruct",
        label: "Delete",
        value: true
      },
      cancelAction: {
        type: "cancel",
        label: "Cancel",
        value: false
      },
      items: ["Item 1", "Item 2", "Item 3"],
      itemType: "items"
    };

    await TestBed.configureTestingModule({
      imports: [SimpleConfirmationDialogComponent],
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

    fixture = TestBed.createComponent(SimpleConfirmationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
