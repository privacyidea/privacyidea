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
import { Clipboard } from "@angular/cdk/clipboard";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NotificationService } from "@services/notification/notification.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockNotificationService } from "@testing/mock-services";
import { SystemDocumentationDialogComponent } from "./system-documentation-dialog.component";

describe("SystemDocumentationDialogComponent", () => {
  let fixture: ComponentFixture<SystemDocumentationDialogComponent>;
  let component: SystemDocumentationDialogComponent;
  let dialogRef: MockMatDialogRef<SystemDocumentationDialogComponent>;
  let notificationService: MockNotificationService;
  let clickedAnchors: HTMLAnchorElement[];
  let createdBlobs: Blob[];
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  beforeEach(async () => {
    dialogRef = new MockMatDialogRef<SystemDocumentationDialogComponent>();
    await TestBed.configureTestingModule({
      imports: [SystemDocumentationDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { documentation: "Some documentation" } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SystemDocumentationDialogComponent);
    component = fixture.componentInstance;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();

    // jsdom neither creates object URLs nor follows links, the files and links the dialog opens are recorded instead
    clickedAnchors = [];
    createdBlobs = [];
    window.URL.createObjectURL = jest.fn((blob: Blob) => {
      createdBlobs.push(blob);
      return "blob:documentation";
    });
    window.URL.revokeObjectURL = jest.fn();
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clickedAnchors.push(this);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("shows the documentation it was handed, under the shared dialog heading", () => {
    expect(fixture.nativeElement.querySelector(".pi-dialog-header").textContent).toContain("System Documentation");
    expect(fixture.nativeElement.querySelector("textarea").value).toBe("Some documentation");
  });

  it("closes on the footer button the wrapper renders", () => {
    fixture.nativeElement.querySelector(".pi-dialog-footer button").click();

    expect(dialogRef.close).toHaveBeenCalled();
  });

  it("offers to copy, download and send the documentation by email", () => {
    const footer = fixture.nativeElement.querySelector(".pi-dialog-footer").textContent;

    for (const label of ["Close", "Copy", "Download", "Send by email"]) {
      expect(footer).toContain(label);
    }
  });

  it("copies the documentation to the clipboard", () => {
    const copy = jest.spyOn(TestBed.inject(Clipboard), "copy").mockReturnValue(true);

    component.onAction("copy");

    expect(copy).toHaveBeenCalledWith("Some documentation");
    expect(notificationService.success).toHaveBeenCalled();
  });

  it("reports a copy the browser refused", () => {
    jest.spyOn(TestBed.inject(Clipboard), "copy").mockReturnValue(false);

    component.onAction("copy");

    expect(notificationService.error).toHaveBeenCalled();
  });

  it("downloads the documentation as a file named after the server and the day", () => {
    component.onAction("download");

    expect(clickedAnchors).toHaveLength(1);
    expect(clickedAnchors[0].download).toMatch(/^privacyidea-system-documentation-.*-\d{4}-\d{2}-\d{2}\.rst$/);
    expect(createdBlobs[0].type).toBe("text/plain");
    expect(createdBlobs[0].size).toBe("Some documentation".length);
  });

  it("downloads the documentation and opens an email that asks to attach it", () => {
    component.onAction("mail");

    expect(clickedAnchors).toHaveLength(2);
    expect(clickedAnchors[0].download).toBe(component.fileName);
    const mailto = clickedAnchors[1].href;
    expect(mailto.startsWith("mailto:?subject=")).toBe(true);
    expect(decodeURIComponent(mailto)).toContain(component.fileName);
    expect(notificationService.info).toHaveBeenCalled();
  });
});
