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
import { ResyncOTPTokenDialog } from "./resync-otp-token-dialog.component";

describe("ResyncOTPTokenDialog", () => {
  let component: ResyncOTPTokenDialog;
  let fixture: ComponentFixture<ResyncOTPTokenDialog>;
  let dialogRef: MockMatDialogRef<ResyncOTPTokenDialog>;

  async function setup(data: boolean) {
    await TestBed.configureTestingModule({
      imports: [ResyncOTPTokenDialog],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: MatDialogRef, useClass: MockMatDialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ResyncOTPTokenDialog);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<ResyncOTPTokenDialog>;
    fixture.detectChanges();
  }

  describe("success state (data = true)", () => {
    beforeEach(async () => setup(true));

    it("should create", () => {
      expect(component).toBeTruthy();
    });

    it("should show success title", () => {
      const title: HTMLElement = fixture.nativeElement.querySelector("h3");
      expect(title.textContent).toContain("Token Resync Successful");
    });

    it("should show success message", () => {
      const paragraph: HTMLElement = fixture.nativeElement.querySelector("p");
      expect(paragraph.textContent).toContain("successfully synchronized");
    });
  });

  describe("failure state (data = false)", () => {
    beforeEach(async () => setup(false));

    it("should create", () => {
      expect(component).toBeTruthy();
    });

    it("should show failure title", () => {
      const title: HTMLElement = fixture.nativeElement.querySelector("h3");
      expect(title.textContent).toContain("Token Resync Failed");
    });

    it("should show failure message", () => {
      const paragraph: HTMLElement = fixture.nativeElement.querySelector("p");
      expect(paragraph.textContent).toContain("could not be synchronized");
    });
  });

  describe("close button", () => {
    beforeEach(async () => setup(true));

    it("should close the dialog when the close button is clicked", () => {
      const closeButton: HTMLButtonElement = fixture.nativeElement.querySelector("button");
      closeButton.click();
      expect(dialogRef.close).toHaveBeenCalled();
    });
  });
});
