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
  EnrollmentResponseDetail,
  TokenService,
} from '../../../../services/token/token.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { lastValueFrom, Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { PasskeyApiPayloadMapper } from '../../../../mappers/token-api-payload/passkey-token-api-payload.mapper';
import { DialogService } from '../../../../services/dialog/dialog.service';
import { MatDialogRef } from '@angular/material/dialog';
import { TokenEnrollmentFirstStepDialogComponent } from '../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';

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
    (basicOptions: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();
  @Output() reopenCurrentEnrollmentDialogChange = new EventEmitter<
    () =>
      | Promise<EnrollmentResponse | void>
      | Observable<EnrollmentResponse | void>
  >();

  passkeyForm = new FormGroup({});

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private enrollmentMapper: PasskeyApiPayloadMapper,
    private dialogService: DialogService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = async (
    basicOptions: TokenEnrollmentData,
  ): Promise<EnrollmentResponse | null> => {
    if (!navigator.credentials?.create) {
      const errorMsg = 'Passkey/WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      throw new Error(errorMsg);
    }

    const enrollmentInitData: PasskeyEnrollmentOptions = {
      ...basicOptions,
      type: 'passkey',
    };

    const responseStepOne = await lastValueFrom(
      this.tokenService.enrollToken({
        data: enrollmentInitData,
        mapper: this.enrollmentMapper,
      }),
    ).catch((error: any) => {
      const errMsg = `Passkey registration process failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      throw new Error(error);
    });

    const detail = responseStepOne.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.openSnackBar(
        'Failed to initiate Passkey registration: Invalid server response.',
      );
      throw new Error('Invalid server response for Passkey initiation.');
    }
    this.openStepOneDialog({ responseStepOne, detail });
    const publicKeyCred = await this.readPublicKeyCred(responseStepOne);
    if (publicKeyCred === null) {
      console.log('Returning null due to credential creation failure');
      return null;
    }
    const resposeLastStep = await this.finalizeEnrollment({
      detail,
      publicKeyCred,
    });
    return resposeLastStep;
  };

  private async finalizeEnrollment(args: {
    detail: EnrollmentResponseDetail;
    publicKeyCred: any;
  }): Promise<EnrollmentResponse> {
    const { detail, publicKeyCred } = args;
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
    return lastValueFrom(this.tokenService.enrollToken(params)).catch(
      async (errorStep3) => {
        this.notificationService.openSnackBar(
          'Error during final Passkey registration step. Attempting to clean up token.',
        );
        await lastValueFrom(this.tokenService.deleteToken(detail.serial)).catch(
          () => {
            this.notificationService.openSnackBar(
              `Failed to delete token ${detail.serial} after registration error. Please check manually.`,
            );
            throw new Error(errorStep3);
          },
        ),
          this.notificationService.openSnackBar(
            `Token ${detail.serial} deleted due to registration error.`,
          );
        throw Error(errorStep3);
      },
    );
  }

  private async readPublicKeyCred(
    responseStepOne: EnrollmentResponse,
  ): Promise<any | null> {
    const detail = responseStepOne.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.openSnackBar(
        'Failed to initiate Passkey registration: Invalid server response.',
      );
      return null; // Return null to handle the error gracefully
    }
    const excludedCredentials = passkeyRegOptions.excludeCredentials.map(
      (cred: any) => ({
        id: this.base64Service.base64URLToBytes(cred.id),
        type: cred.type,
      }),
    );

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: passkeyRegOptions.rp,
      user: {
        id: this.base64Service.base64URLToBytes(passkeyRegOptions.user.id),
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
    console.log('PublicKeyCredentialCreationOptions:', publicKeyOptions);
    const publicKeyCred = await navigator.credentials
      .create({ publicKey: publicKeyOptions })
      .catch((browserOrCredentialError) => {
        this.notificationService.openSnackBar(
          `Passkey credential creation failed: ${browserOrCredentialError.message}`,
        );
        return null; // Return null to handle the error gracefully
      })
      .finally(() => {
        // Ensure the dialog is closed regardless of success or failure
        console.log('Closing Step One dialog after credential creation');
        this.closeStepOneDialog();
      }); // Type assertion to any for compatibility

    console.log('PublicKeyCredential created:', publicKeyCred);
    return publicKeyCred;
  }

  openStepOneDialog(args: {
    responseStepOne: EnrollmentResponse;
    detail: EnrollmentResponseDetail;
  }): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    const { responseStepOne, detail } = args;
    this.reopenCurrentEnrollmentDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen()) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { response: responseStepOne },
          disableClose: true,
        });
        const publicKeyCred = this.readPublicKeyCred(responseStepOne);
        const resposeLastStep = await this.finalizeEnrollment({
          detail,
          publicKeyCred,
        });
        return resposeLastStep;
      }
      return undefined;
    });

    return this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { response: responseStepOne },
      disableClose: true,
    });
  }
  closeStepOneDialog(): void {
    this.reopenCurrentEnrollmentDialogChange.emit(undefined);
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
