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
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  PrivacyideaServer,
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface
} from "../../../../services/privacyidea-server/privacyidea-server.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import {
  ConfirmationDialogComponent,
  ConfirmationDialogResult
} from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

@Component({
  selector: "app-privacyidea-edit-dialog",
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
    MatProgressSpinnerModule
  ],
  templateUrl: "./new-privacyidea-server.component.html",
  styleUrl: "./new-privacyidea-server.component.scss"
})
export class NewPrivacyideaServerComponent implements OnInit, OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewPrivacyideaServerComponent>);
  protected readonly data = inject<PrivacyideaServer | null>(MAT_DIALOG_DATA);
  protected readonly privacyideaServerService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly pendingChangesService = inject(PendingChangesService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  privacyideaForm!: FormGroup;
  isEditMode = false;
  isTesting = signal(false);

  constructor() {
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.onCancel();
      });
      this.dialogRef.keydownEvents().subscribe(event => {
        if (event.key === "Escape") {
          this.onCancel();
        }
      });
    }

    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA)) {
        this.dialogRef?.close(true);
      }
    });
  }

  get hasChanges(): boolean {
    return !this.privacyideaForm.pristine;
  }

  get canSave(): boolean {
    return this.authService.rights().includes("privacyidea_write") && this.privacyideaForm.valid;
  }

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    this.privacyideaForm = this.formBuilder.group({
      identifier: [this.data?.identifier || "", [Validators.required]],
      url: [this.data?.url || "", [Validators.required]],
      tls: [this.data?.tls ?? true],
      description: [this.data?.description || ""],
      username: [this.data?.username || ""],
      password: [this.data?.password || ""]
    });

    if (this.isEditMode) {
      this.privacyideaForm.get("identifier")?.disable();
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.unregisterHasChanges();
  }

  save(): Promise<void> | void {
    if (this.privacyideaForm.valid) {
      const server: PrivacyideaServer = {
        ...this.privacyideaForm.getRawValue()
      };
      return this.privacyideaServerService.postPrivacyideaServer(server).then(() => {
        this.dialogRef.close(true);
      });
    }
  }

  test(): void {
    if (this.privacyideaForm.valid) {
      this.isTesting.set(true);
      const params = this.privacyideaForm.getRawValue();
      this.privacyideaServerService.testPrivacyideaServer(params).then(() => {
        this.isTesting.set(false);
      });
    }
  }

  onCancel(): void {
    if (this.hasChanges) {
      this.dialog
        .open(ConfirmationDialogComponent, {
          data: {
            title: $localize`Discard changes`,
            action: "discard",
            type: "privacyidea-server",
            allowSaveExit: true,
            saveExitDisabled: !this.canSave
          }
        })
        .afterClosed()
        .subscribe((result: ConfirmationDialogResult | undefined) => {
          if (result === "discard") {
            this.pendingChangesService.unregisterHasChanges();
            this.closeActual();
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then(() => {
              this.pendingChangesService.unregisterHasChanges();
              this.closeActual();
            });
          }
        });
    } else {
      this.closeActual();
    }
  }

  private closeActual(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
    }
  }
}
