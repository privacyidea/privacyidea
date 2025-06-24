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
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { WebAuthnApiPayloadMapper } from '../../../../mappers/token-api-payload/webauthn-token-api-payload.mapper';
import { DialogService } from '../../../../services/dialog/dialog.service';

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
  @Output() reopenCurrentEnrollmentDialogChange = new EventEmitter<
    () =>
      | Promise<EnrollmentResponse | void>
      | Observable<EnrollmentResponse | void>
  >();

  // WebAuthn has no form fields in this component to be filled directly by the user
  webauthnForm = new FormGroup({});

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private dialog: MatDialog,
    private enrollmentMapper: WebAuthnApiPayloadMapper,
    private dialogService: DialogService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit((data) => from(this.onClickEnroll(data)));
  }

  onClickEnroll = async (
    enrollmentData: TokenEnrollmentData,
  ): Promise<EnrollmentResponse> => {
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
    ).catch((error) => {
      this.notificationService.openSnackBar(
        `WebAuthn registration process failed: ${error.message || error}`,
      );
      throw error;
    });
    this.openStepOneDialog(enrollmentInitResponse);
    const finalEnrollmentResponse = await this.registerWebauthn(
      enrollmentInitResponse.detail,
    ).finally(() => {
      this.closeStepOneDialog();
    });

    return finalEnrollmentResponse;
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
  openStepOneDialog(response: EnrollmentResponse): void {
    this.reopenCurrentEnrollmentDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen()) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { response },
          disableClose: true,
        });
        return response;
      }
      return undefined;
    });

    this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { response },
      disableClose: true,
    });
  }
  closeStepOneDialog(): void {
    this.reopenCurrentEnrollmentDialogChange.emit(undefined);
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
