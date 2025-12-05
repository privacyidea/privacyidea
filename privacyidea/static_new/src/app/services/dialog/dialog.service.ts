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

// class MatDialogConfigRequired<D = ConfirmationDialogData> extends MatDialogConfig<D> {
//   override data!: D;

//   constructor(data: D) {
//     super();
//     if (!data) {
//       throw new Error("Dialog data is required");
//     }
//     this.data = data;
//   }
// }

export interface DialogServiceInterface {
  openDialogs: Set<MatDialogRef<any, any>>;
  closeDialog<R>(ref: MatDialogRef<any, R>, result?: R): boolean;
  openDialog<T, R>(args: {
    component: ComponentType<AbstractDialogComponent<T, R>>;
    data: T;
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
    data: T;
    configOverride?: Partial<MatDialogConfig<T>>;
  }): MatDialogRef<T, R> {
    const { component, data, configOverride } = args;
    const config: MatDialogConfig<T> = {
      disableClose: true,
      width: "500px",
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
   * Schließt einen spezifischen geöffneten Dialog.
   * @param ref Die MatDialogRef des zu schließenden Dialogs.
   * @param result Der optionale Rückgabewert des Dialogs.
   * @returns true, wenn der Dialog gefunden und geschlossen wurde.
   */
  /**
   *
   * @param ref
   * @param result
   * @returns
   */
  closeDialog<R>(ref: MatDialogRef<any, R>, result?: R): boolean {
    // 1. Schließe den Dialog über die MatDialogRef
    if (this.openDialogs.has(ref)) {
      // Wenn das Ergebnis definiert ist, verwende es, sonst schließe ohne Ergebnis
      ref.close(result);

      // 2. Das afterClosed() Abonnement im openDialog() entfernt die Referenz automatisch
      // aus this.openDialogs, daher ist hier kein manuelles Löschen nötig!
      return true;
    }
    return false;
  }

  // private readonly authService: AuthServiceInterface = inject(AuthService);
  // private readonly router: Router = inject(Router);

  // readonly isSelfServing = computed(() => this.authService.role() === "user");

  // private _tokenEnrollmentFirstStepRef: MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> | null = null;

  // get tokenEnrollmentFirstStepRef() {
  //   return this._tokenEnrollmentFirstStepRef;
  // }

  // get isTokenEnrollmentFirstStepDialogOpen(): boolean {
  //   return this._tokenEnrollmentFirstStepRef !== null;
  // }

  // private _tokenEnrollmentLastStepRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent, any> | null = null;

  // get tokenEnrollmentLastStepRef() {
  //   return this._tokenEnrollmentLastStepRef;
  // }

  // get isTokenEnrollmentLastStepDialogOpen(): boolean {
  //   return this._tokenEnrollmentLastStepRef !== null;
  // }

  // openTokenEnrollmentFirstStepDialog(
  //   config: MatDialogConfigRequired<{ enrollmentResponse: EnrollmentResponse }>
  // ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
  //   if (this._tokenEnrollmentFirstStepRef) {
  //     this._tokenEnrollmentFirstStepRef.close();
  //   }
  //   this._tokenEnrollmentFirstStepRef = this.dialog.open(TokenEnrollmentFirstStepDialogComponent, config);

  //   this._tokenEnrollmentFirstStepRef.afterClosed().subscribe(() => {
  //     this._tokenEnrollmentFirstStepRef = null;
  //   });

  //   return this._tokenEnrollmentFirstStepRef;
  // }

  // closeTokenEnrollmentFirstStepDialog(): void {
  //   this._tokenEnrollmentFirstStepRef?.close();
  // }

  // async openTokenEnrollmentLastStepDialog(
  //   config: MatDialogConfigRequired<TokenEnrollmentLastStepDialogData>
  // ): Promise<MatDialogRef<any>> {
  //   if (this._tokenEnrollmentLastStepRef) {
  //     this._tokenEnrollmentLastStepRef.close();
  //   }

  //   const [
  //     { TokenEnrollmentLastStepDialogComponent },
  //     { TokenEnrollmentLastStepDialogSelfServiceComponent },
  //     { TokenEnrollmentLastStepDialogWizardComponent }
  //   ] = await Promise.all([
  //     import(
  //       "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component"
  //     ),
  //     import(
  //       "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component"
  //     ),
  //     import(
  //       "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.wizard.component"
  //     )
  //   ]);

  //   const isWizardRoute = this.router.url.includes(ROUTE_PATHS.TOKENS_WIZARD);
  //   const component = this.isSelfServing()
  //     ? isWizardRoute
  //       ? TokenEnrollmentLastStepDialogWizardComponent
  //       : TokenEnrollmentLastStepDialogSelfServiceComponent
  //     : TokenEnrollmentLastStepDialogComponent;

  //   this._tokenEnrollmentLastStepRef = this.dialog.open(component as any, config);

  //   this._tokenEnrollmentLastStepRef.afterClosed().subscribe(() => {
  //     this._tokenEnrollmentLastStepRef = null;
  //   });

  //   return this._tokenEnrollmentLastStepRef;
  // }

  // closeTokenEnrollmentLastStepDialog(): void {
  //   this._tokenEnrollmentLastStepRef?.close();
  // }

  // confirm(config: MatDialogConfigRequired<ConfirmationDialogData>): Promise<boolean> {
  //   return new Promise((resolve) => {
  //     const dialogRef = this.dialog.open<ConfirmationDialogComponent, ConfirmationDialogData, boolean>(
  //       ConfirmationDialogComponent,
  //       config
  //     );

  //     dialogRef.afterClosed().subscribe((result) => resolve(result ?? false));
  //   });
  // }

  isAnyDialogOpen(): boolean {
    return this.dialog.openDialogs.length > 0;
  }
}
