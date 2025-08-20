import { computed, inject, Injectable } from "@angular/core";
import { MatDialog, MatDialogConfig, MatDialogRef } from "@angular/material/dialog";

import {
  ConfirmationDialogComponent,
  ConfirmationDialogData
} from "../../components/shared/confirmation-dialog/confirmation-dialog.component";
import { TokenEnrollmentFirstStepDialogComponent } from "../../components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import {
  TokenEnrollmentLastStepDialogComponent,
  TokenEnrollmentLastStepDialogData
} from "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { EnrollmentResponse } from "../../mappers/token-api-payload/_token-api-payload.mapper";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { TokenEnrollmentLastStepDialogSelfServiceComponent } from "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component";

class MatDialogConfigRequired<D = any> extends MatDialogConfig<D> {
  override data!: D;

  constructor(data: D) {
    super();
    if (!data) {
      throw new Error("Dialog data is required");
    }
    this.data = data;
  }
}

export interface DialogServiceInterface {
  isSelfServing: () => boolean;
  tokenEnrollmentFirstStepRef: MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> | null;
  isTokenEnrollmentFirstStepDialogOpen: boolean;
  tokenEnrollmentLastStepRef: MatDialogRef<TokenEnrollmentLastStepDialogComponent, any> | null;
  isTokenEnrollmentLastStepDialogOpen: boolean;

  openTokenEnrollmentFirstStepDialog(
    config: MatDialogConfigRequired<{ enrollmentResponse: EnrollmentResponse }>
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any>;

  closeTokenEnrollmentFirstStepDialog(): void;

  openTokenEnrollmentLastStepDialog(
    config: MatDialogConfigRequired<TokenEnrollmentLastStepDialogData>
  ): Promise<MatDialogRef<any>>;

  closeTokenEnrollmentLastStepDialog(): void;

  confirm(config: MatDialogConfigRequired<ConfirmationDialogData>): Promise<boolean>;

  isAnyDialogOpen(): boolean;
}

@Injectable({ providedIn: "root" })
export class DialogService implements DialogServiceInterface {
  private readonly dialog: MatDialog = inject(MatDialog);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  readonly isSelfServing = computed(() => this.authService.role() === "user");

  private _tokenEnrollmentFirstStepRef: MatDialogRef<
    TokenEnrollmentFirstStepDialogComponent,
    any
  > | null = null;

  get tokenEnrollmentFirstStepRef() {
    return this._tokenEnrollmentFirstStepRef;
  }

  get isTokenEnrollmentFirstStepDialogOpen(): boolean {
    return this._tokenEnrollmentFirstStepRef !== null;
  }

  private _tokenEnrollmentLastStepRef: MatDialogRef<
    TokenEnrollmentLastStepDialogComponent,
    any
  > | null = null;

  get tokenEnrollmentLastStepRef() {
    return this._tokenEnrollmentLastStepRef;
  }

  get isTokenEnrollmentLastStepDialogOpen(): boolean {
    return this._tokenEnrollmentLastStepRef !== null;
  }

  openTokenEnrollmentFirstStepDialog(
    config: MatDialogConfigRequired<{ enrollmentResponse: EnrollmentResponse }>
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    if (this._tokenEnrollmentFirstStepRef) {
      this._tokenEnrollmentFirstStepRef.close();
    }
    this._tokenEnrollmentFirstStepRef = this.dialog.open(
      TokenEnrollmentFirstStepDialogComponent,
      config
    );

    this._tokenEnrollmentFirstStepRef.afterClosed().subscribe(() => {
      this._tokenEnrollmentFirstStepRef = null;
    });

    return this._tokenEnrollmentFirstStepRef;
  }

  closeTokenEnrollmentFirstStepDialog(): void {
    this._tokenEnrollmentFirstStepRef?.close();
  }

  async openTokenEnrollmentLastStepDialog(
    config: MatDialogConfigRequired<TokenEnrollmentLastStepDialogData>
  ): Promise<MatDialogRef<any>> {
    if (this._tokenEnrollmentLastStepRef) {
      this._tokenEnrollmentLastStepRef.close();
    }

    const [
      { TokenEnrollmentLastStepDialogComponent },
      { TokenEnrollmentLastStepDialogSelfServiceComponent }
    ] = await Promise.all([
      import(
        "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component"
        ),
      import(
        "../../components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.self-service.component"
        )
    ]);

    const component = this.isSelfServing()
      ? TokenEnrollmentLastStepDialogSelfServiceComponent
      : TokenEnrollmentLastStepDialogComponent;

    this._tokenEnrollmentLastStepRef = this.dialog.open(component as any, config);

    this._tokenEnrollmentLastStepRef.afterClosed().subscribe(() => {
      this._tokenEnrollmentLastStepRef = null;
    });

    return this._tokenEnrollmentLastStepRef;
  }

  closeTokenEnrollmentLastStepDialog(): void {
    this._tokenEnrollmentLastStepRef?.close();
  }

  confirm(config: MatDialogConfigRequired<ConfirmationDialogData>): Promise<boolean> {
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
