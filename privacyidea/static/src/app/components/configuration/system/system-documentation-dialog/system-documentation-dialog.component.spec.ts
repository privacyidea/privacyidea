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
import { Clipboard, PendingCopy } from "@angular/cdk/clipboard";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NotificationService } from "@services/notification/notification.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockNotificationService } from "@testing/mock-services";
import {
  COPY_ATTEMPTS,
  SystemDocumentationDialogComponent,
  systemDocumentationFileName
} from "./system-documentation-dialog.component";

describe("SystemDocumentationDialogComponent", () => {
  let fixture: ComponentFixture<SystemDocumentationDialogComponent>;
  let component: SystemDocumentationDialogComponent;
  let dialogRef: MockMatDialogRef<SystemDocumentationDialogComponent>;
  let notificationService: MockNotificationService;
  let clickedAnchors: HTMLAnchorElement[];
  let createdBlobs: Blob[];
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  const pendingCopy = (...results: boolean[]) => {
    const copy = jest.fn();
    results.forEach((result) => copy.mockReturnValueOnce(result));
    const pending = { copy, destroy: jest.fn() };
    jest.spyOn(TestBed.inject(Clipboard), "beginCopy").mockReturnValue(pending as unknown as PendingCopy);
    return pending;
  };

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

    // The retries of a copy and the release of a download run on timers
    jest.useFakeTimers();
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
    jest.clearAllTimers();
    jest.useRealTimers();
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

  it("focuses the download when it opens, not the email", () => {
    expect(fixture.nativeElement.querySelector("[cdkFocusInitial]").textContent).toContain("Download");
  });

  it("copies the documentation to the clipboard", () => {
    const pending = pendingCopy(true);

    component.onAction("copy");

    expect(TestBed.inject(Clipboard).beginCopy).toHaveBeenCalledWith("Some documentation");
    expect(pending.destroy).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalled();
  });

  it("tries a copy the browser refused again", () => {
    const pending = pendingCopy(false, true);

    component.onAction("copy");
    jest.runAllTimers();

    expect(pending.copy).toHaveBeenCalledTimes(2);
    expect(notificationService.success).toHaveBeenCalled();
    expect(notificationService.error).not.toHaveBeenCalled();
  });

  it("reports a copy the browser refused on every attempt", () => {
    const pending = pendingCopy(...Array(COPY_ATTEMPTS).fill(false));

    component.onAction("copy");
    jest.runAllTimers();

    expect(pending.copy).toHaveBeenCalledTimes(COPY_ATTEMPTS);
    expect(pending.destroy).toHaveBeenCalled();
    expect(notificationService.error).toHaveBeenCalled();
  });

  it("offers no sharing where the browser can not share files", () => {
    expect(fixture.nativeElement.querySelector(".pi-dialog-footer").textContent).not.toContain("Share");
  });

  describe("where the browser can share files", () => {
    let share: jest.Mock;

    beforeEach(() => {
      share = jest.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "canShare", { configurable: true, value: jest.fn(() => true) });
      Object.defineProperty(navigator, "share", { configurable: true, value: share });
      fixture = TestBed.createComponent(SystemDocumentationDialogComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    });

    afterEach(() => {
      delete (navigator as Partial<Navigator>).canShare;
      delete (navigator as Partial<Navigator>).share;
    });

    it("offers to share the documentation", () => {
      expect(fixture.nativeElement.querySelector(".pi-dialog-footer").textContent).toContain("Share");
    });

    it("shares the documentation as a text file named after the server and the day", async () => {
      await component.shareDocumentation();

      const data = share.mock.calls[0][0] as ShareData;
      expect(data.files).toHaveLength(1);
      expect(data.files?.[0]).toBe(component.shareFile);
      expect(component.shareFile.name).toMatch(/^privacyidea-system-documentation-.*-\d{4}-\d{2}-\d{2}\.txt$/);
      expect(component.shareFile.type).toBe("text/plain");
      expect(component.shareFile.size).toBe("Some documentation".length);
      expect(data.text).toContain(component.shareFile.name);
      expect(notificationService.error).not.toHaveBeenCalled();
    });

    it("stays quiet when the share dialog is closed without sharing", async () => {
      share.mockRejectedValue(new DOMException("Share canceled", "AbortError"));

      await component.shareDocumentation();

      expect(notificationService.error).not.toHaveBeenCalled();
    });

    it("reports a share the browser refused", async () => {
      share.mockRejectedValue(new DOMException("Permission denied", "NotAllowedError"));

      await component.shareDocumentation();

      expect(notificationService.error).toHaveBeenCalled();
    });
  });

  it("downloads the documentation as a file named after the server and the day", () => {
    component.onAction("download");

    expect(clickedAnchors).toHaveLength(1);
    expect(clickedAnchors[0].download).toMatch(/^privacyidea-system-documentation-.*-\d{4}-\d{2}-\d{2}\.rst$/);
    expect(createdBlobs[0].type).toBe("text/plain");
    expect(createdBlobs[0].size).toBe("Some documentation".length);
  });

  it("downloads the documentation and opens an email in a new window that asks to attach it", () => {
    component.onAction("mail");

    expect(clickedAnchors).toHaveLength(2);
    expect(clickedAnchors[0].download).toBe(component.fileName);
    const mailto = clickedAnchors[1];
    expect(mailto.href.startsWith("mailto:?subject=")).toBe(true);
    expect(mailto.target).toBe("_blank");
    expect(decodeURIComponent(mailto.href)).toContain(component.fileName);
    expect(notificationService.info).toHaveBeenCalled();
  });
});

describe("systemDocumentationFileName", () => {
  it("names the file after the server and the day", () => {
    expect(systemDocumentationFileName("pi.example.com", "2026-10-22")).toBe(
      "privacyidea-system-documentation-pi.example.com-2026-10-22.rst"
    );
  });

  it("takes another extension", () => {
    expect(systemDocumentationFileName("pi.example.com", "2026-10-22", "txt")).toBe(
      "privacyidea-system-documentation-pi.example.com-2026-10-22.txt"
    );
  });

  it("replaces the characters of an IPv6 address a file name does not keep", () => {
    expect(systemDocumentationFileName("[2001:db8::1]", "2026-10-22")).toBe(
      "privacyidea-system-documentation-_2001_db8__1_-2026-10-22.rst"
    );
  });
});
