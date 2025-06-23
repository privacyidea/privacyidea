import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { firstValueFrom, from, Observable, switchMap, throwError } from 'rxjs';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenService,
} from '../../../../services/token/token.service';
import { catchError, finalize, first } from 'rxjs/operators';
import { TokenEnrollmentFirstStepDialogComponent } from '../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { WebauthnEncodingService } from '../../../../services/webauthn-encoding/webauthn-encoding.service';
import { WebAuthnApiPayloadMapper } from '../../../../mappers/token-api-payload/webauthn-token-api-payload.mapper';

// Interface for the initialization options of the WebAuthn token (first step)
export interface WebauthnEnrollmentData extends TokenEnrollmentData {
  type: 'webauthn';
  // No additional type-specific fields for the *first* enrollment call (init)
  // The more complex data is sent in the second step after browser interaction.
}

// Interface for the parameters of the *second* enrollment call (after browser interaction)
export interface WebauthnRegistrationParams {
  type: 'webauthn';
  transaction_id: string;
  serial: string;
  credential_id: string; // ArrayBuffer
  rawId: string; // base64
  authenticatorAttachment: string | null;
  regdata: string; // base64 (attestationObject)
  clientdata: string; // base64 (clientDataJSON)
  credProps?: any;
}

@Component({
  selector: 'app-enroll-webauthn',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-webauthn.component.html',
  styleUrl: './enroll-webauthn.component.scss',
})
export class EnrollWebauthnComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'webauthn')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: TokenEnrollmentData,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  // WebAuthn has no form fields in this component to be filled directly by the user
  webauthnForm = new FormGroup({});

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private dialog: MatDialog,
    private webauthnEncodingService: WebauthnEncodingService,
    private enrollmentMapper: WebAuthnApiPayloadMapper,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit((data) => from(this.onClickEnroll(data)));
  }

  onClickEnroll = async (
    enrollmentData: TokenEnrollmentData,
  ): Promise<EnrollmentResponse> => {
    let firstStepDialogRef:
      | MatDialogRef<TokenEnrollmentFirstStepDialogComponent>
      | undefined;
    const webauthnEnrollmentData: WebauthnEnrollmentData = {
      ...enrollmentData,
      type: 'webauthn',
    };

    // Step 1: Initial enrollment call to get challenge etc.
    const enrollmentInitResponse = await firstValueFrom(
      this.tokenService.enrollToken({
        data: webauthnEnrollmentData,
        mapper: this.enrollmentMapper,
      }),
    )
      .catch((error) => {
        this.notificationService.openSnackBar(
          `WebAuthn registration process failed: ${error.message || error}`,
        );
        throw error;
      })
      .finally(() => {
        if (firstStepDialogRef) {
          firstStepDialogRef.close();
        }
      });
    this.openStepOneDialog(enrollmentInitResponse);
    return this.registerWebauthn(enrollmentInitResponse.detail);
  };

  registerWebauthn = async (
    detail: EnrollmentResponseDetail,
  ): Promise<EnrollmentResponse> => {
    const request = detail?.webAuthnRegisterRequest;
    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: {
        id: request.relyingParty.id,
        name: request.relyingParty.name,
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber),
        name: request.name,
        displayName: request.displayName,
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce),
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred: any) => ({
            id: this.base64Service.base64URLToBytes(cred.id),
            type: cred.type,
            transports: cred.transports,
          }))
        : [],
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation,
      extensions: request.extensions,
    };

    const publicKeyCred = (await navigator.credentials.create({
      publicKey: publicKeyOptions,
    })) as any; // Type assertion to any for compatibility

    const params: any = {
      type: 'webauthn',
      transaction_id: request.transaction_id,
      serial: request.serialNumber,
      credential_id: publicKeyCred.id,
      rawId: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.rawId),
      ),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      regdata: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.response.attestationObject),
      ),
      clientdata: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.response.clientDataJSON),
      ),
    };

    const extResults = publicKeyCred.getClientExtensionResults();
    if (extResults.credProps) {
      params.credProps = extResults.credProps;
    }

    return firstValueFrom(
      this.tokenService.enrollToken({
        data: params,
        mapper: this.enrollmentMapper,
      }),
    );
  };
  openStepOneDialog = (response: EnrollmentResponse): void => {
    this.dialog.open(TokenEnrollmentFirstStepDialogComponent, {
      data: { response },
      disableClose: true,
    });
  };
}

// registerWebauthnNEW = async (
//   webAuthnInitResponse: EnrollmentResponse,
// ): Promise<EnrollmentResponse> => {
//   const detail = webAuthnInitResponse.detail;
//   const requestFromStep1 = detail?.webAuthnRegisterRequest;

//   if (!requestFromStep1) {
//     this.notificationService.openSnackBar(
//       'Failed to initiate WebAuthn registration: Invalid server response.',
//     );
//     throw new Error('Invalid server response for WebAuthn initiation.');
//   }

//   const firstStepDialogRef = this.openStepOneDialog(webAuthnInitResponse);

//   const publicKeyOptions: PublicKeyCredentialCreationOptions = {
//     rp: {
//       id: requestFromStep1.relyingParty?.id,
//       name: requestFromStep1.relyingParty.name,
//     },
//     user: {
//       id: new TextEncoder().encode(requestFromStep1.serialNumber),
//       name: requestFromStep1.name,
//       displayName: requestFromStep1.displayName,
//     },
//     challenge: this.base64Service.base64URLToBytes(requestFromStep1.nonce),
//     pubKeyCredParams: requestFromStep1.pubKeyCredAlgorithms,
//     timeout: requestFromStep1.timeout,
//     excludeCredentials: requestFromStep1.excludeCredentials
//       ? requestFromStep1.excludeCredentials.map((cred: any) => ({
//           id: this.base64Service.base64URLToBytes(cred.id),
//           type: cred.type,
//           transports: cred.transports,
//         }))
//       : [],
//     authenticatorSelection: requestFromStep1.authenticatorSelection,
//     attestation: requestFromStep1.attestation,
//     extensions: requestFromStep1.extensions,
//   };

//   // Step 2: Browser API interaction

//   const publicKeyCred = (await navigator.credentials.create({
//     publicKey: publicKeyOptions,
//   })) as any; // Type assertion to any for compatibility

//   // Step 3: Final enrollment call with browser response

//   if (!publicKeyCred) {
//     throw new Error('WebAuthn credential creation failed.');
//   }
//   const params: any = {
//     // Parameters for the second /token/init call (finalize registration)
//     type: 'webauthn',
//     transaction_id: requestFromStep1.transaction_id,
//     serial: requestFromStep1.serialNumber,
//     credential_id: publicKeyCred.id, // This is an ArrayBuffer
//     rawId: this.base64Service.bytesToBase64(
//       new Uint8Array(publicKeyCred.rawId),
//     ),
//     authenticatorAttachment: publicKeyCred.authenticatorAttachment,
//     regdata: this.webauthnEncodingService.encodeWebAuthnBase64(
//       new Uint8Array(publicKeyCred.response.attestationObject), // attestationObject is ArrayBuffer, needs web-safe base64
//     ),
//     clientdata: this.webauthnEncodingService.encodeWebAuthnBase64(
//       new Uint8Array(publicKeyCred.response.clientDataJSON),
//     ), // clientDataJSON is ArrayBuffer, needs web-safe base64
//   };

//   const extResults = publicKeyCred.getClientExtensionResults();
//   if (extResults?.credProps) {
//     params.credProps = extResults.credProps;
//   }
//   const observable = this.tokenService.enrollToken(params).pipe(
//     catchError((errorStep3) => {
//       // Attempt to delete the token if the finalization fails
//       // The serial number is available from the first step response
//       const serialToDelete = requestFromStep1.serialNumber;
//       this.notificationService.openSnackBar(
//         'Error during final WebAuthn registration step. Attempting to clean up token.',
//       );
//       return from(
//         this.tokenService.deleteToken(requestFromStep1.serialNumber),
//       ).pipe(
//         switchMap(() => {
//           this.notificationService.openSnackBar(
//             `Token ${serialToDelete} deleted due to registration error.`,
//           );
//           return throwError(() => errorStep3);
//         }),
//         catchError((deleteError) => {
//           this.notificationService.openSnackBar(
//             `Failed to delete token ${serialToDelete} after registration error. Please check manually.`,
//           );
//           return throwError(() => errorStep3);
//         }),
//       );
//     }),
//   );
//   return firstValueFrom(observable);
// };

/*
        this.openFirstStepDialog(response);
        this.enrollWebauthnComponent.registerWebauthn(detail).subscribe({
          next: () => {
            this.pollTokenRolloutState(detail.serial, 2000);
          },
        });
        break;
*/

/*
  private pollTokenRolloutState(tokenSerial: string, startTime: number) {
    return this.tokenService
      .pollTokenRolloutState(tokenSerial, startTime)
      .subscribe({
        next: (pollResponse: any) => {
          this.pollResponse.set(pollResponse);
          if (
            pollResponse.result.value.tokens[0].rollout_state !== 'clientwait'
          ) {
            this.firstDialog.closeAll();
            this.openSecondStepDialog(this.enrollResponse());
            this.notificationService.openSnackBar(
              `Token ${tokenSerial} enrolled successfully.`,
            );
          }
        },
      });
  }
*/

/*


import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { from, Observable, switchMap, throwError } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { TokenService } from '../../../../services/token/token.service';
import { catchError } from 'rxjs/operators';

@Component({
  selector: 'app-enroll-webauthn',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-webauthn.component.html',
  styleUrl: './enroll-webauthn.component.scss',
})
export class EnrollWebauthnComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'webauthn')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() enrollResponse!: WritableSignal<any>;
  @Input() firstDialog!: MatDialog;

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
  ) {}

*/
