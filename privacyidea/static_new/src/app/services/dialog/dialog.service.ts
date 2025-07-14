import { computed, Injectable } from '@angular/core';
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
  ConfirmationDialogComponent,
  ConfirmationDialogData,
} from '../../components/shared/confirmation-dialog/confirmation-dialog.component';
import { AuthService } from '../auth/auth.service';

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
  readonly isSelfServing = computed(() => this.authService.role() === 'user');

  private _tokenEnrollmentFirstStepRef: MatDialogRef<
    TokenEnrollmentFirstStepDialogComponent,
    any
  > | null = null;

  constructor(
    private dialog: MatDialog,
    private authService: AuthService,
  ) {}

  private _tokenEnrollmentLastStepRef: MatDialogRef<
    TokenEnrollmentLastStepDialogComponent,
    any
  > | null = null;

  get tokenEnrollmentLastStepRef() {
    return this._tokenEnrollmentLastStepRef;
  }

  openTokenEnrollmentFirstStepDialog(
    config: MatDialogConfigRequired<{ enrollmentResponse: EnrollmentResponse }>,
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    if (this._tokenEnrollmentFirstStepRef) {
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
    this._tokenEnrollmentFirstStepRef?.close();
  }

  openTokenEnrollmentLastStepDialog(
    config: MatDialogConfigRequired<TokenEnrollmentLastStepDialogData>,
  ): MatDialogRef<TokenEnrollmentLastStepDialogComponent, any> {
    if (this._tokenEnrollmentLastStepRef) {
      this._tokenEnrollmentLastStepRef.close();
    }

    const component = this.isSelfServing()
      ? (
          require('../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component') as typeof import('../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component')
        ).TokenEnrollmentLastStepDialogSelfServiceComponent
      : TokenEnrollmentLastStepDialogComponent;

    this._tokenEnrollmentLastStepRef = this.dialog.open(
      component as any,
      config,
    );

    this._tokenEnrollmentLastStepRef.afterClosed().subscribe(() => {
      this._tokenEnrollmentLastStepRef = null;
    });

    return this._tokenEnrollmentLastStepRef;
  }

  closeTokenEnrollmentLastStepDialog(): void {
    this._tokenEnrollmentLastStepRef?.close();
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

      dialogRef.afterClosed().subscribe((result) => resolve(result ?? false));
    });
  }

  isAnyDialogOpen(): boolean {
    return this.dialog.openDialogs.length > 0;
  }
}
