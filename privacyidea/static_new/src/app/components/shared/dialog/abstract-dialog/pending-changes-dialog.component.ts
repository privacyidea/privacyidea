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

import { DestroyRef, Directive, inject, OnDestroy, OnInit, Signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import { PendingChangesService } from "src/app/services/pending-changes/pending-changes.service";

@Directive()
export abstract class PendingChangesDialogComponent<D = any, R = any>
  extends AbstractDialogComponent<D, R>
  implements OnInit, OnDestroy {
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly pendingChangesService: PendingChangesService = inject(PendingChangesService);
  private readonly destroyRef = inject(DestroyRef);

  abstract canSave: Signal<boolean>;
  abstract isDirty: Signal<boolean>;

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(this.isDirty);
    this.pendingChangesService.registerValidChanges(this.canSave);
    this.pendingChangesService.registerSave(this.onSave.bind(this));
    this.dialogRef.disableClose = true;
    this.dialogRef
      .backdropClick()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.handleCloseAttempt();
      });
    this.dialogRef
      .keydownEvents()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        if (event.key === "Escape") {
          this.handleCloseAttempt();
        }
      });
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  abstract onSave(): Promise<boolean>;

  protected async handleCloseAttempt(): Promise<void> {
    if (!this.isDirty()) {
      this.dialogRef.close();
      return;
    }
    const result = await this.dialogService.openDialogAsync({
      component: SaveAndExitDialogComponent,
      data: {
        saveExitDisabled: !this.canSave(),
        allowSaveExit: true
      }
    });

    if (result === "discard") {
      this.dialogRef.close();
    } else if (result === "save-exit") {
      const saveSuccessful = await this.onSave();
      if (saveSuccessful) {
        this.dialogRef.close();
      }
    }
  }

  override close(dialogResult?: R | undefined): void {
    this.handleCloseAttempt();
  }
}
