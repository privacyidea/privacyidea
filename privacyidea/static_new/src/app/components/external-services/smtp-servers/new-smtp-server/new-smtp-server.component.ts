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

import { Component, inject, OnInit, signal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { SmtpServer, SmtpService, SmtpServiceInterface } from "../../../../services/smtp/smtp.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-smtp-edit-dialog",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip
  ],
  templateUrl: "./new-smtp-server.component.html",
  styleUrl: "./new-smtp-server.component.scss"
})
export class NewSmtpServerComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewSmtpServerComponent>);
  protected readonly data = inject<SmtpServer | null>(MAT_DIALOG_DATA);
  protected readonly smtpService: SmtpServiceInterface = inject(SmtpService);

  smtpForm!: FormGroup;
  isEditMode = false;
  isTesting = signal(false);

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    this.smtpForm = this.fb.group({
      identifier: [this.data?.identifier || "", [Validators.required]],
      server: [this.data?.server || "", [Validators.required]],
      port: [this.data?.port || 25],
      timeout: [this.data?.timeout || 10],
      sender: [this.data?.sender || "", [Validators.required, Validators.email]],
      username: [this.data?.username || ""],
      password: [this.data?.password || ""],
      description: [this.data?.description || ""],
      tls: [this.data?.tls ?? true],
      enqueue_job: [this.data?.enqueue_job ?? false],
      recipient: [""]
    });

    if (this.isEditMode) {
      this.smtpForm.get("identifier")?.disable();
    }
  }

  save(): void {
    if (this.smtpForm.valid) {
      const server: SmtpServer = {
        ...this.smtpForm.getRawValue()
      };
      this.smtpService.postSmtpServer(server).then(() => {
        this.dialogRef.close(true);
      });
    }
  }

  test(): void {
    if (this.smtpForm.valid) {
      this.isTesting.set(true);
      const params = this.smtpForm.getRawValue();
      this.smtpService.testSmtpServer(params).then(() => {
        this.isTesting.set(false);
      });
    }
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
