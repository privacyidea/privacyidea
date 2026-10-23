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
import { CdkTextareaAutosize } from "@angular/cdk/text-field";
import { formatDate } from "@angular/common";
import { AfterViewInit, Component, ElementRef, inject, ViewChild } from "@angular/core";

import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { downloadBlob } from "@utils/download.utils";

export type SystemDocumentationAction = "copy" | "share" | "download" | "mail";

/**
 * Copying a long text to the clipboard can fail on the first attempt, so it is tried a few times.
 */
export const COPY_ATTEMPTS = 3;

/**
 * Names the file after the server and the day, so that the documentation of several installations can be told apart.
 * Characters a browser does not keep in a file name, like the brackets and colons of an IPv6 address, are replaced.
 */
export function systemDocumentationFileName(server: string, date: string, extension = "rst"): string {
  return `privacyidea-system-documentation-${server.replace(/[^A-Za-z0-9.-]/g, "_")}-${date}.${extension}`;
}

@Component({
  selector: "app-system-documentation-dialog",
  templateUrl: "./system-documentation-dialog.component.html",
  standalone: true,
  imports: [MatFormField, MatLabel, MatInput, CdkTextareaAutosize, DialogWrapperComponent]
})
export class SystemDocumentationDialogComponent
  extends AbstractDialogComponent<{ documentation: string }>
  implements AfterViewInit
{
  private readonly clipboard = inject(Clipboard);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  @ViewChild("autosize", { read: ElementRef }) textareaElement!: ElementRef<HTMLTextAreaElement>;
  documentation = this.data.documentation || "";

  private readonly server = window.location.hostname;
  private readonly date = formatDate(new Date(), "yyyy-MM-dd", "en-US");
  readonly fileName = systemDocumentationFileName(this.server, this.date);
  private readonly emailSubject = $localize`:@@systemConfig.documentationEmailSubject:privacyIDEA system documentation of ${this.server}:server: from ${this.date}:date:`;

  /**
   * The share dialog of the operating system passes the file on, e.g. to the email program as an attachment. Chrome
   * shares only files of a few known extensions, .txt among them but not .rst.
   */
  readonly shareFile = new File([this.documentation], systemDocumentationFileName(this.server, this.date, "txt"), {
    type: "text/plain"
  });
  private readonly canShare =
    typeof navigator.canShare === "function" && navigator.canShare({ files: [this.shareFile] });

  readonly actions: DialogAction<SystemDocumentationAction>[] = [
    {
      type: "auxiliary",
      label: $localize`:@@common.copy:Copy`,
      value: "copy",
      icon: "content_copy",
      className: "button-width-m"
    },
    {
      type: "auxiliary",
      label: $localize`:@@systemConfig.shareDocumentation:Share`,
      value: "share",
      icon: "share",
      hidden: !this.canShare,
      className: "button-width-m"
    },
    {
      type: "auxiliary",
      label: $localize`:@@systemConfig.sendDocumentationByEmail:Send by email`,
      value: "mail",
      icon: "mail",
      className: "button-width-m"
    },
    {
      type: "confirm",
      label: $localize`:@@systemConfig.downloadDocumentation:Download`,
      value: "download",
      icon: "download",
      primary: true,
      className: "button-width-m"
    }
  ];

  ngAfterViewInit(): void {
    setTimeout(() => {
      const element = this.textareaElement?.nativeElement as HTMLTextAreaElement | undefined;
      if (element) {
        try {
          element.setSelectionRange(0, 0);
        } catch {
          // setSelectionRange may throw in some browser environments; ignore
        }
        element.scrollTop = 0;
      }
    });
  }

  onAction(action: SystemDocumentationAction): void {
    switch (action) {
      case "copy":
        this.copyDocumentation();
        break;
      case "share":
        void this.shareDocumentation();
        break;
      case "download":
        this.downloadDocumentation();
        break;
      case "mail":
        this.sendDocumentationByEmail();
        break;
    }
  }

  copyDocumentation(): void {
    const pendingCopy = this.clipboard.beginCopy(this.documentation);
    let remainingAttempts = COPY_ATTEMPTS;
    const attempt = (): void => {
      remainingAttempts--;
      const copied = pendingCopy.copy();
      if (!copied && remainingAttempts > 0) {
        setTimeout(attempt);
        return;
      }
      pendingCopy.destroy();
      if (copied) {
        this.notificationService.success(
          $localize`:@@systemConfig.documentationCopied:The system documentation was copied to the clipboard.`
        );
      } else {
        this.notificationService.error(
          $localize`:@@systemConfig.documentationNotCopied:The system documentation could not be copied to the clipboard.`
        );
      }
    };
    attempt();
  }

  async shareDocumentation(): Promise<void> {
    try {
      await navigator.share({
        files: [this.shareFile],
        title: this.emailSubject,
        text: this.emailBody(this.shareFile.name)
      });
    } catch (error) {
      // Closing the share dialog without choosing where to share to rejects the share as well
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.notificationService.error(
          $localize`:@@systemConfig.documentationNotShared:The system documentation could not be shared.`
        );
      }
    }
  }

  downloadDocumentation(): void {
    downloadBlob(new Blob([this.documentation], { type: "text/plain" }), this.fileName);
  }

  /**
   * An email link can not carry an attachment, and the text of the documentation is too long for the body of one:
   * the documentation is downloaded, and the email program is opened with a message that asks to attach it.
   * The email link opens in a new window. Opened in the window of the WebUI, it would ask whether to leave a page
   * with unsaved changes, a web mail service would replace the WebUI, and the download could be cut off.
   */
  sendDocumentationByEmail(): void {
    this.downloadDocumentation();
    const anchor = document.createElement("a");
    anchor.href = `mailto:?subject=${encodeURIComponent(this.emailSubject)}&body=${encodeURIComponent(this.emailBody(this.fileName))}`;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    anchor.click();
    this.notificationService.info(
      $localize`:@@systemConfig.documentationEmailAttach:The system documentation was downloaded as ${this.fileName}:fileName:. Attach it to the email.`
    );
  }

  private emailBody(fileName: string): string {
    return $localize`:@@systemConfig.documentationEmailBody:The system documentation of privacyIDEA is attached as ${fileName}:fileName:.`;
  }
}
