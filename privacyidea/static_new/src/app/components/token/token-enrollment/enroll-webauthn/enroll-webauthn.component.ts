import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { firstValueFrom, from, lastValueFrom, Observable } from 'rxjs';
import { TokenService } from '../../../../services/token/token.service';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebauthnEnrollmentResponse,
  WebauthnEnrollmentResponseDetail,
  WebauthnFinalizeData,
} from '../../../../mappers/token-api-payload/webauthn-token-api-payload.mapper';
import { DialogService } from '../../../../services/dialog/dialog.service';

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
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
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
    private enrollmentMapper: WebAuthnApiPayloadMapper,
    private dialogService: DialogService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit((data) => from(this.onClickEnroll(data)));
  }

  onClickEnroll = async (
    basicEnrollmentData: TokenEnrollmentData,
  ): Promise<EnrollmentResponse | null> => {
    if (!navigator.credentials?.create) {
      const errorMsg = 'WebAuthn/WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      throw new Error(errorMsg);
    }

    const webauthnEnrollmentData: WebAuthnEnrollmentData = {
      ...basicEnrollmentData,
      type: 'webauthn',
    };

    const webauthnEnrollmentResponse = await lastValueFrom(
      this.tokenService.enrollToken<
        WebAuthnEnrollmentData,
        WebauthnEnrollmentResponse
      >({
        data: webauthnEnrollmentData,
        mapper: this.enrollmentMapper,
      }),
    ).catch((error: any) => {
      const errMsg = `WebAuthn registration process failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      throw new Error(errMsg);
    });

    const detail = webauthnEnrollmentResponse.detail;

    const webAuthnRegOptions = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegOptions) {
      this.notificationService.openSnackBar(
        'Failed to initiate WebAuthn registration: Invalid server response.',
      );
      throw new Error('Invalid server response for WebAuthn initiation.');
    }
    this.openStepOneDialog({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse,
    });

    const resposeLastStep = await this.finalizeEnrollment({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse,
    });

    if (!resposeLastStep) {
      return null; // If the enrollment failed, return null
    }
    return resposeLastStep;
  };

  readPublicKeyCred = async (
    enrollmentResponse: WebauthnEnrollmentResponse,
  ): Promise<any | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;
    const publicKeyOptions: any = {
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

    const publicKeyCred = await navigator.credentials
      .create({
        publicKey: publicKeyOptions,
      })
      .catch((browserOrCredentialError) => {
        this.notificationService.openSnackBar(
          `WebAuthn credential creation failed: ${browserOrCredentialError.message}`,
        );
        return null; // Return null to handle the error gracefully
      })
      .finally(() => {
        // Ensure the dialog is closed regardless of success or failure

        this.closeStepOneDialog();
      }); // Type assertion to any for compatibility

    return publicKeyCred;
  };

  /*
detail: {
  "rollout_state": "clientwait",
  "serial": "WAN00635BC9",
  "threadid": 128468883609152,
  "webAuthnRegisterRequest": {
    "attestation": "direct",
    "authenticatorSelection": {
      "userVerification": "preferred"
    },
    "displayName": "<sys.deflocal@defrealm>",
    "message": "Bitte bestätigen Sie mit Ihrem WebAuthn Token",
    "name": "sys",
    "nonce": "vWE6OpoN5LtfhIONHUHzAmBxTtugYM2A4C-O_8K9nj4",
    "pubKeyCredAlgorithms": [
      {
        "alg": -7,
        "type": "public-key"
      },
      {
        "alg": -37,
        "type": "public-key"
      },
      {
        "alg": -257,
        "type": "public-key"
      }
    ],
    "relyingParty": {
      "id": "pi.frank",
      "name": "Frank Test"
    },
    "serialNumber": "WAN00635BC9",
    "timeout": 60000,
    "transaction_id": "09229186815681229188"
  }
}
   */

  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
    // publicKeyCred: any;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;
    console.log('enrollmentResponse is set:', !!webauthnEnrollmentResponse);
    const detail = webauthnEnrollmentResponse.detail;
    console.log('enrollmentResponse detail is set:', !!detail);
    console.log('detail: ', detail);
    if (!detail.transaction_id || !detail.serial) {
      throw new Error(
        'Invalid transaction ID or serial number in enrollment detail.',
      );
    }

    const publicKeyCred = await this.readPublicKeyCred(
      webauthnEnrollmentResponse,
    );
    if (publicKeyCred === null) {
      return null;
    }

    const params: WebauthnFinalizeData = {
      ...webauthnEnrollmentData,
      transaction_id: detail.transaction_id,
      serial: detail.serial,
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
  }

  openStepOneDialog(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): void {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;
    this.reopenCurrentEnrollmentDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen()) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { enrollmentResponse: webauthnEnrollmentResponse },
          disableClose: true,
        });
        this.finalizeEnrollment({
          webauthnEnrollmentData,
          webauthnEnrollmentResponse,
        });
        return webauthnEnrollmentResponse;
      }
      return undefined;
    });

    this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse: webauthnEnrollmentResponse },
      disableClose: true,
    });
  }
  closeStepOneDialog(): void {
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
