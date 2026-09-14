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
import { CdkTextareaAutosize } from "@angular/cdk/text-field";
import { AfterViewInit, Component, ElementRef, inject, ViewChild } from "@angular/core";

import { MatButton } from "@angular/material/button";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";

@Component({
  selector: "app-system-documentation-dialog",
  templateUrl: "./system-documentation-dialog.component.html",
  styleUrls: ["./system-documentation-dialog.component.scss"],
  standalone: true,
  imports: [MatDialogModule, MatFormField, MatLabel, MatInput, MatButton, CdkTextareaAutosize, CopyableComponent]
})
export class SystemDocumentationDialogComponent implements AfterViewInit {
  @ViewChild("autosize", { read: ElementRef }) textareaElement!: ElementRef<HTMLTextAreaElement>;
  documentation = "";

  public dialogRef = inject(MatDialogRef<SystemDocumentationDialogComponent>);
  public data: { documentation: string } = inject(MAT_DIALOG_DATA);

  constructor() {
    this.documentation = this.data.documentation || "";
  }

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

  onClose(): void {
    this.dialogRef.close();
  }
}
