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
import { MessageDialogComponent, MessageDialogData } from "./message-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { DialogWrapperComponent } from "../dialog-wrapper/dialog-wrapper.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("MessageDialogComponent", () => {
  let component: MessageDialogComponent;
  let fixture: ComponentFixture<MessageDialogComponent>;
  let dialogRef: MatDialogRef<MessageDialogComponent>;

  const mockDialogRef = {
    close: () => {}
  };

  const dialogData: MessageDialogData = {
    title: "Test Title",
    texts: ["Line 1", "Line 2"]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, MessageDialogComponent, DialogWrapperComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MessageDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef);
    jest.spyOn(dialogRef, "close");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the title and texts", () => {
    const titleElement: HTMLElement = fixture.nativeElement.querySelector("h2");
    expect(titleElement.textContent).toContain("Test Title");

    const textElements: NodeListOf<HTMLDivElement> = fixture.nativeElement.querySelectorAll(".text-center div");
    expect(textElements.length).toBe(2);
    expect(textElements[0].textContent).toContain("Line 1");
    expect(textElements[1].textContent).toContain("Line 2");
  });

  it("should display the icon", () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, MessageDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            ...dialogData,
            icon: "test_icon"
          }
        }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(MessageDialogComponent);
    fixture.detectChanges();
    const iconElement = fixture.nativeElement.querySelector("mat-icon");
    expect(iconElement).toBeTruthy();
    expect(iconElement.textContent).toBe("test_icon");
  });

  it("should not display the icon", () => {
    const iconElement = fixture.nativeElement.querySelector("mat-icon");
    expect(iconElement).toBeFalsy();
  });

  it('should display "Information" as default title', () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, MessageDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    });

    const localFixture = TestBed.createComponent(MessageDialogComponent);
    localFixture.detectChanges();

    const titleElement: HTMLElement = localFixture.nativeElement.querySelector("h2");
    expect(titleElement.textContent).toContain("Information");
  });

  it("should close the dialog", () => {
    (component as any).close();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it("should work with empty texts", () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, MessageDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            ...dialogData,
            texts: []
          }
        }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(MessageDialogComponent);
    fixture.detectChanges();
    const textElements: NodeListOf<HTMLDivElement> = fixture.nativeElement.querySelectorAll(".text-center div");
    expect(textElements.length).toBe(0);
  });
});
