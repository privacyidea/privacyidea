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
import { inject, Injectable } from "@angular/core";
import { MatDialog, MatDialogConfig, MatDialogRef } from "@angular/material/dialog";
import { ComponentType } from "@angular/cdk/overlay";
import { take } from "rxjs";
import { AbstractDialogComponent } from "../../components/shared/dialog/abstract-dialog/abstract-dialog.component";

export interface DialogServiceInterface {
  openDialogs: Set<MatDialogRef<any, any>>;
  closeDialog<R>(ref: MatDialogRef<any, R>, result?: R): boolean;
  openDialog<T, R>(args: {
    component: ComponentType<AbstractDialogComponent<T, R>>;
    data?: T;
    configOverride?: Partial<MatDialogConfig<T>>;
  }): MatDialogRef<T, R>;

  closeLatestDialog(): void;
  closeAllDialogs(): void;
  isAnyDialogOpen(): boolean;
}

@Injectable({ providedIn: "root" })
export class DialogService implements DialogServiceInterface {
  private readonly dialog: MatDialog = inject(MatDialog);
  public openDialogs = new Set<MatDialogRef<any, any>>();
  closeAllDialogs(): void {
    this.dialog.closeAll();
    this.openDialogs.clear();
  }
  closeLatestDialog(): void {
    const latestRef = Array.from(this.openDialogs).pop();
    if (latestRef) {
      latestRef.close();
    }
  }

  /**
   * Opens a dialog.
   * @param T - The type of the payload data in MatDialogConfig.data.
   * @param R - The type of the return value when the dialog is closed.
   */
  openDialog<T, R>(args: {
    component: ComponentType<AbstractDialogComponent<T, R>>;
    data?: T;
    configOverride?: Partial<MatDialogConfig<T>>;
  }): MatDialogRef<T, R> {
    const { component, data, configOverride } = args;
    const config: MatDialogConfig<T> = {
      disableClose: false,
      hasBackdrop: true,
      data,
      ...configOverride
    };
    const dialogRef = this.dialog.open(component, config) as MatDialogRef<T, R>;
    this.openDialogs.add(dialogRef);
    dialogRef
      .afterClosed()
      .pipe(take(1))
      .subscribe(() => {
        this.openDialogs.delete(dialogRef);
      });

    return dialogRef;
  }

  /**
   * @param ref The MatDialogRef of the dialog to be closed.
   * @param result The optional return value of the dialog.
   * @returns true if the dialog was found and closed.
   */
  closeDialog<R>(ref: MatDialogRef<any, R>, result?: R): boolean {
    if (this.openDialogs.has(ref)) {
      ref.close(result);
      return true;
    }
    return false;
  }

  isAnyDialogOpen(): boolean {
    return this.dialog.openDialogs.length > 0;
  }
}
