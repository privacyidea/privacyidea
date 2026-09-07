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
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog.component";

describe("SystemDocumentationDialogComponent", () => {
  let fixture: ComponentFixture<SystemDocumentationDialogComponent>;
  let dialogRef: MockMatDialogRef<SystemDocumentationDialogComponent>;

  beforeEach(async () => {
    dialogRef = new MockMatDialogRef<SystemDocumentationDialogComponent>();
    await TestBed.configureTestingModule({
      imports: [SystemDocumentationDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { documentation: "Some documentation" } },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SystemDocumentationDialogComponent);
    fixture.detectChanges();
  });

  it("shows the documentation it was handed, under the shared dialog heading", () => {
    expect(fixture.nativeElement.querySelector(".pi-dialog-header").textContent).toContain("System Documentation");
    expect(fixture.nativeElement.querySelector("textarea").value).toBe("Some documentation");
  });

  it("closes on the footer button the wrapper renders", () => {
    fixture.nativeElement.querySelector(".pi-dialog-footer button").click();

    expect(dialogRef.close).toHaveBeenCalled();
  });
});
