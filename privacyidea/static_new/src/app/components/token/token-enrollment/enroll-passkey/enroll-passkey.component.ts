import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import {
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { from, Observable, switchMap, throwError, of } from 'rxjs';
import { catchError, finalize, tap } from 'rxjs/operators';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { TokenEnrollmentFirstStepDialogComponent } from '../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { PasskeyApiPayloadMapper } from '../../../../mappers/token-api-payload/passkey-token-api-payload.mapper';

// Interface for the initialization options of the Passkey token (first step)
export interface PasskeyEnrollmentOptions extends TokenEnrollmentData {
  type: 'passkey';
  // No additional type-specific fields for the *first* enrollment call (init)
}

// Interface for the parameters of the *second* enrollment call (after browser interaction)
export interface PasskeyRegistrationParams {
  // Does not extend TokenEnrollmentData as it's a specific payload
  type: 'passkey';
  transaction_id: string;
  serial: string;
  credential_id: string; // ArrayBuffer
  rawId: string; // base64
  authenticatorAttachment: string | null;
  attestationObject: string; // base64
  clientDataJSON: string; // base64
  credProps?: any;
}

@Component({
  selector: 'app-enroll-passkey',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule],
  templateUrl: './enroll-passkey.component.html',
  styleUrl: './enroll-passkey.component.scss',
})
export class EnrollPasskeyComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'passkey')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  passkeyForm = new FormGroup({});

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private dialog: MatDialog,
    private enrollmentMapper: PasskeyApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: TokenEnrollmentData,
  ): Observable<EnrollmentResponse> | undefined => {
    if (!navigator.credentials?.create) {
      const errorMsg = 'Passkey/WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      return throwError(() => new Error(errorMsg));
    }

    let firstStepDialogRef:
      | MatDialogRef<TokenEnrollmentFirstStepDialogComponent>
      | undefined;
    const enrollmentInitData: PasskeyEnrollmentOptions = {
      ...basicOptions,
      type: 'passkey',
    };

    return this.tokenService
      .enrollToken({
        data: enrollmentInitData,
        mapper: this.enrollmentMapper,
      })
      .pipe(
        switchMap((responseStep1) => {
          const detail = responseStep1.detail;
          const passkeyRegOptions = detail?.passkey_registration;

          if (!passkeyRegOptions) {
            this.notificationService.openSnackBar(
              'Failed to initiate Passkey registration: Invalid server response.',
            );
            return throwError(
              () =>
                new Error('Invalid server response for Passkey initiation.'),
            );
          }

          firstStepDialogRef = this.dialog.open(
            TokenEnrollmentFirstStepDialogComponent,
            {
              data: { response: responseStep1 },
              disableClose: true,
            },
          );

          const excludedCredentials = passkeyRegOptions.excludeCredentials.map(
            (cred: any) => ({
              id: this.base64Service.base64URLToBytes(cred.id),
              type: cred.type,
            }),
          );

          const publicKeyOptions: PublicKeyCredentialCreationOptions = {
            rp: passkeyRegOptions.rp,
            user: {
              id: this.base64Service.base64URLToBytes(
                passkeyRegOptions.user.id,
              ),
              name: passkeyRegOptions.user.name,
              displayName: passkeyRegOptions.user.displayName,
            },
            challenge: this.base64Service.base64URLToBytes(
              passkeyRegOptions.challenge,
            ),
            pubKeyCredParams: passkeyRegOptions.pubKeyCredParams,
            excludeCredentials: excludedCredentials,
            authenticatorSelection: passkeyRegOptions.authenticatorSelection,
            timeout: passkeyRegOptions.timeout,
            extensions: { credProps: true, ...passkeyRegOptions.extensions },
            attestation: passkeyRegOptions.attestation,
          };

          return from(
            navigator.credentials.create({ publicKey: publicKeyOptions }),
          ).pipe(
            switchMap((publicKeyCred: any) => {
              if (!publicKeyCred) {
                return throwError(
                  () => new Error('Passkey credential creation failed.'),
                );
              }
              const params: any = {
                type: 'passkey',
                transaction_id: detail.transaction_id!,
                serial: detail.serial,
                credential_id: publicKeyCred.id,
                rawId: this.base64Service.bytesToBase64(
                  new Uint8Array(publicKeyCred.rawId),
                ),
                authenticatorAttachment: publicKeyCred.authenticatorAttachment,
                attestationObject: this.base64Service.bytesToBase64(
                  new Uint8Array(publicKeyCred.response.attestationObject),
                ),
                clientDataJSON: this.base64Service.bytesToBase64(
                  new Uint8Array(publicKeyCred.response.clientDataJSON),
                ),
              };

              const extResults = publicKeyCred.getClientExtensionResults();
              if (extResults?.credProps) {
                params.credProps = extResults.credProps;
              }
              return this.tokenService.enrollToken(params).pipe(
                catchError((errorStep3) => {
                  this.notificationService.openSnackBar(
                    'Error during final Passkey registration step. Attempting to clean up token.',
                  );
                  return from(
                    this.tokenService.deleteToken(detail.serial),
                  ).pipe(
                    switchMap(() => {
                      this.notificationService.openSnackBar(
                        `Token ${detail.serial} deleted due to registration error.`,
                      );
                      return throwError(() => errorStep3);
                    }),
                    catchError((deleteError) => {
                      this.notificationService.openSnackBar(
                        `Failed to delete token ${detail.serial} after registration error. Please check manually.`,
                      );
                      return throwError(() => errorStep3);
                    }),
                  );
                }),
              );
            }),
            catchError((browserOrCredentialError) => {
              this.notificationService.openSnackBar(
                `Passkey credential creation failed: ${browserOrCredentialError.message}`,
              );
              return throwError(() => browserOrCredentialError);
            }),
          );
        }),
        catchError((error: any) => {
          const errMsg = `Passkey registration process failed: ${error.message || error}`;
          this.notificationService.openSnackBar(errMsg);
          return throwError(() => error);
        }),
        finalize(() => {
          if (firstStepDialogRef) {
            firstStepDialogRef.close();
          }
        }),
      );
  };
}
