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
  MessageConfirmationDialogComponent,
  MessageConfirmationDialogData
} from "./message-confirmation-dialog.component";

describe("MessageConfirmationDialogComponent", () => {
  let component: MessageConfirmationDialogComponent;
  let fixture: ComponentFixture<MessageConfirmationDialogComponent>;
  let dialogRef: MockMatDialogRef<MessageConfirmationDialogComponent, boolean>;

  const setup = async (data: Partial<MessageConfirmationDialogData> = {}) => {
    TestBed.resetTestingModule();
    dialogRef = new MockMatDialogRef<MessageConfirmationDialogComponent, boolean>();

    await TestBed.configureTestingModule({
      imports: [MessageConfirmationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            title: "Cancel Enrollment",
            message: "The enrollment can still be completed as soon as the device is online again.",
            confirmAction: { type: "destruct", label: "Delete", value: true },
            ...data
          }
        },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MessageConfirmationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  const footerButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));

  it("should create", async () => {
    await setup();
    expect(component).toBeTruthy();
  });

  it("renders the title and the plain message without a generated question", async () => {
    await setup();

    expect(fixture.nativeElement.textContent).toContain("Cancel Enrollment");
    expect(fixture.nativeElement.textContent).toContain(
      "The enrollment can still be completed as soon as the device is online again."
    );
    expect(fixture.nativeElement.textContent).not.toContain("Are you sure");
    expect(fixture.nativeElement.querySelector("ul")).toBeNull();
  });

  it("shows the confirm action next to the close button and marks it primary", async () => {
    await setup();

    expect(footerButtons().map((button) => button.textContent?.trim())).toEqual(["Cancel", "Delete"]);
    expect(component.actions[0].primary).toBe(true);
  });

  it("keeps an explicit primary flag from the caller", async () => {
    await setup({ confirmAction: { type: "confirm", label: "Proceed", value: true, primary: false } });

    expect(component.actions[0].primary).toBe(false);
  });

  it("closes with true when the confirm action is triggered", async () => {
    await setup();

    component.onAction(true);

    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it("closes without a result when the dialog is dismissed", async () => {
    await setup();

    footerButtons()[0].click();

    expect(dialogRef.close).toHaveBeenCalled();
    expect(dialogRef.close.mock.calls[0][0]).toBeUndefined();
  });
});
