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
import { AfterViewInit, Component, ElementRef, inject, ViewChild } from "@angular/core";

import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";

export type SystemDocumentationAction = "copy" | "download" | "mail";

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

  // The server and the day name the file, so that the documentation of several installations can be told apart
  private readonly server = window.location.hostname;
  private readonly date = new Date().toISOString().slice(0, 10);
  readonly fileName = `privacyidea-system-documentation-${this.server}-${this.date}.rst`;

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
      label: $localize`:@@systemConfig.downloadDocumentation:Download`,
      value: "download",
      icon: "download",
      className: "button-width-m"
    },
    {
      type: "confirm",
      label: $localize`:@@systemConfig.sendDocumentationByEmail:Send by email`,
      value: "mail",
      icon: "mail",
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
      case "download":
        this.downloadDocumentation();
        break;
      case "mail":
        this.sendDocumentationByEmail();
        break;
    }
  }

  copyDocumentation(): void {
    if (this.clipboard.copy(this.documentation)) {
      this.notificationService.success(
        $localize`:@@systemConfig.documentationCopied:The system documentation was copied to the clipboard.`
      );
    } else {
      this.notificationService.error(
        $localize`:@@systemConfig.documentationNotCopied:The system documentation could not be copied to the clipboard.`
      );
    }
  }

  downloadDocumentation(): void {
    const url = window.URL.createObjectURL(new Blob([this.documentation], { type: "text/plain" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = this.fileName;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * An email link can not carry an attachment, and the text of the documentation is too long for the body of one:
   * the documentation is downloaded, and the email program is opened with a message that asks to attach it.
   */
  sendDocumentationByEmail(): void {
    this.downloadDocumentation();
    const subject = $localize`:@@systemConfig.documentationEmailSubject:privacyIDEA system documentation of ${this.server}:server: from ${this.date}:date:`;
    const body = $localize`:@@systemConfig.documentationEmailBody:The system documentation of privacyIDEA is attached as ${this.fileName}:fileName:.`;
    const anchor = document.createElement("a");
    anchor.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    anchor.click();
    this.notificationService.info(
      $localize`:@@systemConfig.documentationEmailAttach:The system documentation was downloaded as ${this.fileName}:fileName:. Attach it to the email.`
    );
  }
}
