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
import { RadiusServer, RadiusService, RadiusServiceInterface } from "../../../../services/radius/radius.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import {
  ConfirmationDialogComponent,
  ConfirmationDialogResult
} from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { Router } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";

@Component({
  selector: "app-new-radius-server",
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
  templateUrl: "./new-radius-server.component.html",
  styleUrl: "./new-radius-server.component.scss"
})
export class NewRadiusServerComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<NewRadiusServerComponent>);
  protected readonly data = inject<RadiusServer | null>(MAT_DIALOG_DATA);
  protected readonly radiusService: RadiusServiceInterface = inject(RadiusService);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly pendingChangesService = inject(PendingChangesService);

  radiusForm!: FormGroup;
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
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS)) {
        this.dialogRef?.close(true);
      }
    });
  }

  get hasChanges(): boolean {
    return !this.radiusForm.pristine;
  }

  get canSave(): boolean {
    return this.radiusForm.valid;
  }

  ngOnInit(): void {
    this.isEditMode = !!this.data;
    this.radiusForm = this.fb.group({
      identifier: [this.data?.identifier || "", [Validators.required]],
      server: [this.data?.server || "", [Validators.required]],
      port: [this.data?.port || 1812],
      timeout: [this.data?.timeout || 5],
      retries: [this.data?.retries || 3],
      secret: [this.data?.secret || "", [Validators.required]],
      message_authenticator: [this.data?.options?.message_authenticator ?? true],
      dictionary: [this.data?.dictionary || ""],
      description: [this.data?.description || ""],
      username: [""],
      password: [""]
    });

    if (this.isEditMode) {
      this.radiusForm.get("identifier")?.disable();
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.unregisterHasChanges();
  }

  save(): Promise<void> | void {
    if (this.radiusForm.valid) {
      const formValue = this.radiusForm.getRawValue();
      const server: RadiusServer = {
        identifier: formValue.identifier,
        server: formValue.server,
        port: formValue.port,
        timeout: formValue.timeout,
        retries: formValue.retries,
        secret: formValue.secret,
        dictionary: formValue.dictionary,
        description: formValue.description,
        options: {
          message_authenticator: formValue.message_authenticator
        }
      };
      return this.radiusService.postRadiusServer(server).then(() => {
        this.dialogRef.close(true);
      });
    }
  }

  test(): void {
    if (this.radiusForm.valid) {
      this.isTesting.set(true);
      const formValue = this.radiusForm.getRawValue();
      const params = {
        ...formValue,
        options: {
          message_authenticator: formValue.message_authenticator
        }
      };
      this.radiusService.testRadiusServer(params).then(() => {
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
            type: "radius-server",
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
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS);
    }
  }
}
