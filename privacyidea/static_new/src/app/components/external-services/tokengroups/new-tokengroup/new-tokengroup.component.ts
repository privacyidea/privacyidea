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
import { Component, effect, inject, OnDestroy } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import {
  Tokengroup,
  TokengroupService,
  TokengroupServiceInterface
} from "../../../../services/tokengroup/tokengroup.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ROUTE_PATHS } from "../../../../route_paths";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-new-tokengroup",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    ClearableInputComponent
  ],
  templateUrl: "./new-tokengroup.component.html",
  styleUrl: "./new-tokengroup.component.scss"
})
export class NewTokengroupComponent implements OnDestroy {
  private readonly formBuilder = inject(FormBuilder);
  protected readonly tokengroupService: TokengroupServiceInterface = inject(TokengroupService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  protected data: Tokengroup | null = null;
  tokengroupForm!: FormGroup;
  isEditMode = false;
  private editGroupName: string | null = null;

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const name = params.get("name");
      if (name) {
        this.isEditMode = true;
        this.editGroupName = name;
        this.data = this.tokengroupService.tokengroups().find((g) => g.groupname === name) ?? null;
      } else {
        this.isEditMode = false;
        this.editGroupName = null;
        this.data = null;
      }
      this.initForm();
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const tokengroups = this.tokengroupService.tokengroups();
      if (this.isEditMode && this.editGroupName && this.tokengroupForm?.pristine) {
        const found = tokengroups.find((g) => g.groupname === this.editGroupName);
        if (found) {
          this.data = found;
          this.initForm();
        }
      }
    });
  }

  get hasChanges(): boolean {
    return !this.tokengroupForm.pristine;
  }

  get canSave(): boolean {
    return this.tokengroupForm.valid;
  }

  private initForm(): void {
    this.tokengroupForm = this.formBuilder.group({
      groupname: [this.data?.groupname || "", [Validators.required]],
      description: [this.data?.description || ""]
    });
    if (this.isEditMode) {
      this.tokengroupForm.get("groupname")?.disable();
    }
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  async save(): Promise<boolean> {
    if (this.tokengroupForm.invalid) {
      return false;
    }
    const group: Tokengroup = {
      ...this.tokengroupForm.getRawValue()
    };

    try {
      await this.tokengroupService.postTokengroup(group);
      this.pendingChangesService.clearAllRegistrations();
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS);
      return true;
    } catch (error) {
      return false;
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
        .subscribe((result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS);
          } else if (result === "save-exit") {
            if (!this.canSave) return;
            Promise.resolve(this.pendingChangesService.save()).then((success) => {
              if (!success) return;
              this.pendingChangesService.clearAllRegistrations();
              this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS);
            });
          }
        });
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS);
    }
  }
}
