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

import { Component, effect, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { SmtpServer, SmtpService, SmtpServiceInterface } from "../../../../services/smtp/smtp.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";

import { MatIconModule } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { MatDivider } from "@angular/material/list";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "../../../../constants/global.constants";

@Component({
  selector: "app-smtp-edit-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatIconModule,
    MatTooltip,
    ClearableInputComponent,
    MatDivider
  ],
  templateUrl: "./new-smtp-server.component.html",
  styleUrl: "./new-smtp-server.component.scss"
})
export class NewSmtpServerComponent implements OnInit, OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewSmtpServerComponent>);
  protected readonly data = inject<SmtpServer | null>(MAT_DIALOG_DATA);
  protected readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly pendingChangesService = inject(PendingChangesService);

  smtpForm!: FormGroup;
  isEditMode = false;
  isTesting = signal(false);

  constructor() {
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.onCancel();
      });
      this.dialogRef.keydownEvents().subscribe((event) => {
        if (event.key === "Escape") {
          this.onCancel();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP)) {
        this.dialogRef?.close(true);
      }
    });
  }

  get hasChanges(): boolean {
    return !this.smtpForm.pristine;
  }

  get canSave(): boolean {
    return this.smtpForm.valid;
  }

  get showTLS(): boolean {
    return !this.smtpForm.get("server")?.value?.toLowerCase().startsWith("smtps:");
  }

  initialPrivateKeyPassword = this.data?.private_key_password || "";

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    this.smtpForm = this.formBuilder.group({
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
      certificate: [this.data?.certificate || ""],
      private_key: [this.data?.private_key || ""],
      private_key_password: [this.data?.private_key_password || ""],
      smime: [this.data?.smime ?? false],
      dont_send_on_error: [this.data?.dont_send_on_error ?? false],
      recipient: [""]
    });

    if (this.isEditMode) {
      this.smtpForm.get("identifier")?.disable();
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  async save(): Promise<boolean> {
    if (this.smtpForm.invalid) {
      return false;
    }
    const server: SmtpServer = {
      ...this.smtpForm.getRawValue()
    };

    if (server.private_key_password === this.initialPrivateKeyPassword) {
      delete server.private_key_password;
    }

    try {
      await this.smtpService.postSmtpServer(server);
      this.dialogRef.close(true);
      return true;
    } catch (error) {
      return false;
    }
  }

  async test(): Promise<void> {
    if (this.smtpForm.valid) {
      this.isTesting.set(true);
      const params = this.smtpForm.getRawValue();
      await this.smtpService.testSmtpServer(params);
      this.isTesting.set(false);
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe(async (result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.closeCurrent();
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            const success = await this.pendingChangesService.save();
            if (!success) return;
            this.pendingChangesService.clearAllRegistrations();
            this.closeCurrent();
          }
        });
    } else {
      this.closeCurrent();
    }
  }

  private closeCurrent(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP);
    }
  }
}
