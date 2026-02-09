/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, Inject } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormsModule } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatButton } from "@angular/material/button";
import { CdkTextareaAutosize } from "@angular/cdk/text-field";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";

@Component({
  selector: "app-system-documentation-dialog",
  templateUrl: "./system-documentation-dialog.component.html",
  styleUrls: ["./system-documentation-dialog.component.scss"],
  standalone: true,
  imports: [
    MatDialogModule,
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatButton,
    CdkTextareaAutosize,
    CopyButtonComponent
  ]
})
export class SystemDocumentationDialogComponent {
  documentation: string = "";

  constructor(
    public dialogRef: MatDialogRef<SystemDocumentationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { documentation: string }
  ) {
    this.documentation = data.documentation || "";
  }

  onClose(): void {
    this.dialogRef.close();
  }
}