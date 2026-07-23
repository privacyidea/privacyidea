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
import { AuditDownloadDialogComponent } from "@components/logs/audit/audit-download-dialog/audit-download-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";

describe("AuditDownloadDialogComponent", () => {
  let component: AuditDownloadDialogComponent;
  let fixture: ComponentFixture<AuditDownloadDialogComponent>;
  let mockDialogRef: MockMatDialogRef<AuditDownloadDialogComponent, boolean>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuditDownloadDialogComponent],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AuditDownloadDialogComponent);
    mockDialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<AuditDownloadDialogComponent, boolean>;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should close the dialog when the Cancel button is clicked", () => {
    const buttons = fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>;
    const cancelButton = Array.from(buttons).find((b) =>
      b.textContent?.includes("Cancel")
    ) as HTMLButtonElement;
    expect(cancelButton).toBeTruthy();
    cancelButton.click();
    fixture.detectChanges();
    expect(mockDialogRef.close).toHaveBeenCalled();
  });

  it("should close the dialog with true when the Start Download button is clicked", () => {
    const buttons = fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>;
    const downloadButton = Array.from(buttons).find((b) =>
      b.textContent?.includes("Proceed")
    ) as HTMLButtonElement;
    expect(downloadButton).toBeTruthy();
    downloadButton.click();
    fixture.detectChanges();
    expect(mockDialogRef.close).toHaveBeenCalledWith(true);
  });
});
