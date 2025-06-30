// src/app/dialogs/dialog.service.ts
import { Injectable } from '@angular/core';
import {
  MatDialog,
  MatDialogConfig,
  MatDialogRef,
} from '@angular/material/dialog';
import {
  TokenEnrollmentLastStepDialogComponent,
  TokenEnrollmentLastStepDialogData,
} from '../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component';
import { TokenEnrollmentFirstStepDialogComponent } from '../../components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';
import { EnrollmentResponse } from '../../mappers/token-api-payload/_token-api-payload.mapper';
import {
  ConfirmationDialogData,
  ConfirmationDialogComponent,
} from '../../components/shared/confirmation-dialog/confirmation-dialog.component';

/* * This class extends MatDialogConfig to ensure that the data property is always required.
 * This is useful for dialogs that require data to be passed in, ensuring that the dialog cannot
 * be opened without the necessary data.
 */
class MatDialogConfigRequired<D = any> extends MatDialogConfig<D> {
  override data!: D;

  constructor(data: D) {
    super();
    if (!data) {
      throw new Error('Dialog data is required');
    }
    this.data = data;
  }
}

@Injectable({ providedIn: 'root' })
export class DialogService {
  constructor(private dialog: MatDialog) {}

  private _tokenEnrollmentFirstStepRef: MatDialogRef<
    TokenEnrollmentFirstStepDialogComponent,
    any
  > | null = null;
  openTokenEnrollmentFirstStepDialog(
    config: MatDialogConfigRequired<{
      enrollmentResponse: EnrollmentResponse;
    }>,
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    if (this._tokenEnrollmentFirstStepRef) {
      // If the dialog is already open, close it before opening a new one
      this._tokenEnrollmentFirstStepRef.close();
    }
    this._tokenEnrollmentFirstStepRef = this.dialog.open(
      TokenEnrollmentFirstStepDialogComponent,
      config,
    );
    this._tokenEnrollmentFirstStepRef.afterClosed().subscribe(() => {
      this._tokenEnrollmentFirstStepRef = null;
    });
    return this._tokenEnrollmentFirstStepRef;
  }

  closeTokenEnrollmentFirstStepDialog(): void {
    if (this._tokenEnrollmentFirstStepRef) {
      this._tokenEnrollmentFirstStepRef.close();
    }
  }
  isTokenEnrollmentFirstStepDialogOpen(): boolean {
    return !!this._tokenEnrollmentFirstStepRef;
  }

  private _tokenEnrollmentLastStepRef: MatDialogRef<
    TokenEnrollmentLastStepDialogComponent,
    any
  > | null = null;
  get tokenEnrollmentLastStepRef() {
    return this._tokenEnrollmentLastStepRef;
  }
  openTokenEnrollmentLastStepDialog(
    config: MatDialogConfigRequired<TokenEnrollmentLastStepDialogData>,
  ): MatDialogRef<TokenEnrollmentLastStepDialogComponent, any> {
    if (this._tokenEnrollmentLastStepRef) {
      // If the dialog is already open, close it before opening a new one
      this._tokenEnrollmentLastStepRef.close();
    }
    this._tokenEnrollmentLastStepRef = this.dialog.open(
      TokenEnrollmentLastStepDialogComponent,
      config,
    );
    this._tokenEnrollmentLastStepRef.afterClosed().subscribe(() => {
      this._tokenEnrollmentLastStepRef = null;
    });
    return this._tokenEnrollmentLastStepRef;
  }

  closeTokenEnrollmentLastStepDialog(): void {
    if (this._tokenEnrollmentLastStepRef) {
      this._tokenEnrollmentLastStepRef.close();
    }
  }

  isTokenEnrollmentLastStepDialogOpen(): boolean {
    return !!this._tokenEnrollmentLastStepRef;
  }

  isAnyDialogOpen(): boolean {
    return this.dialog.openDialogs.length > 0;
  }

  confirm(
    config: MatDialogConfigRequired<ConfirmationDialogData>,
  ): Promise<boolean> {
    return new Promise((resolve) => {
      const dialogRef = this.dialog.open<
        ConfirmationDialogComponent,
        ConfirmationDialogData,
        boolean
      >(ConfirmationDialogComponent, config);

      dialogRef.afterClosed().subscribe((result) => {
        resolve(result ?? false);
      });
    });
  }
}
