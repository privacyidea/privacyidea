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
import { Component, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { Tokengroup, TokengroupService, TokengroupServiceInterface } from "@services/tokengroup/tokengroup.service";

interface TokengroupFormModel {
  groupname: string;
  description: string;
}

const EMPTY_TOKENGROUP_FORM: TokengroupFormModel = {
  groupname: "",
  description: ""
};

@Component({
  selector: "app-new-tokengroup",
  standalone: true,
  imports: [
    FormField,
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
  protected readonly tokengroupService: TokengroupServiceInterface = inject(TokengroupService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly pendingChangesService = inject(PendingChangesService);

  protected data: Tokengroup | null = null;
  isEditMode = signal(false);
  private editGroupName: string | null = null;

  tokengroupModel = signal<TokengroupFormModel>({ ...EMPTY_TOKENGROUP_FORM });

  tokengroupForm = form(this.tokengroupModel, (f) => {
    required(f.groupname);
    pattern(f.groupname, /^[a-zA-Z0-9._-]*$/);
    disabled(f.groupname, () => this.isEditMode());
  });

  constructor() {
    this.pendingChangesService.registerHasChanges(() => this.hasChanges);
    this.pendingChangesService.registerSave(() => this.save());
    this.pendingChangesService.registerValidChanges(() => this.canSave);

    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const name = params.get("name");
      if (name) {
        this.isEditMode.set(true);
        this.editGroupName = name;
        this.data = this.tokengroupService.tokengroups().find((g) => g.groupname === name) ?? null;
      } else {
        this.isEditMode.set(false);
        this.editGroupName = null;
        this.data = null;
      }
      this.loadData(this.data);
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const tokengroups = this.tokengroupService.tokengroups();
      if (this.isEditMode() && this.editGroupName && untracked(() => !this.tokengroupForm().dirty())) {
        const found = tokengroups.find((g) => g.groupname === this.editGroupName);
        if (found) {
          this.data = found;
          this.loadData(this.data);
        }
      }
    });
  }

  get hasChanges(): boolean {
    return this.tokengroupForm().dirty();
  }

  get canSave(): boolean {
    return this.tokengroupForm().valid();
  }

  private loadData(data: Tokengroup | null): void {
    this.tokengroupModel.set({
      groupname: data?.groupname || "",
      description: data?.description || ""
    });
    this.tokengroupForm().reset();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  async save(): Promise<boolean> {
    if (!this.tokengroupForm().valid()) {
      return false;
    }
    const { groupname, description } = this.tokengroupModel();
    const group: Tokengroup = { groupname, description };

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
