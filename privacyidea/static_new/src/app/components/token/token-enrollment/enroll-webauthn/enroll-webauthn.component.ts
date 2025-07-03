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
  // text property to display the token type name, retrieved from TokenService.
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'webauthn')?.text;

  // Output event emitter for additional form fields, though WebAuthn typically has none.
  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  // Output event emitter for the enrollment click handler.
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  // Output event emitter to trigger reopening the current enrollment dialog,
  // used for multi-step enrollment processes.
  @Output() reopenCurrentEnrollmentDialogChange = new EventEmitter<
    () =>
      | Promise<EnrollmentResponse | void>
      | Observable<EnrollmentResponse | void>
  >();

  // WebAuthn has no direct form fields in this component for user input.
  webauthnForm = new FormGroup({});

  // Constructor to inject required services.
  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private enrollmentMapper: WebAuthnApiPayloadMapper,
    private dialogService: DialogService,
  ) {}

  /**
   * Initializes the component. Emits an empty object for additional form fields
   * and registers the onClickEnroll function as the handler for the enrollment button.
   */
  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    // Emit the onClickEnroll function, wrapped in 'from' to convert the Promise to an Observable.
    this.clickEnrollChange.emit((data) => from(this.onClickEnroll(data)));
  }

  /**
   * Handles the WebAuthn enrollment process.
   * This is the main orchestrator for initiating and finalizing WebAuthn registration.
   * @param basicEnrollmentData - Basic enrollment data provided by the parent component.
   * @returns A Promise resolving to EnrollmentResponse on success, or null on failure.
   */
  onClickEnroll = async (
    basicEnrollmentData: TokenEnrollmentData,
  ): Promise<EnrollmentResponse | null> => {
    // 1. Check for WebAuthn API support in the browser.
    if (!navigator.credentials?.create) {
      const errorMsg = 'WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      // Immediately return null as WebAuthn is not supported.
      return null;
    }

    // Prepare WebAuthn-specific enrollment data.
    const webauthnEnrollmentData: WebAuthnEnrollmentData = {
      ...basicEnrollmentData,
      type: 'webauthn',
    };

    let webauthnEnrollmentResponse: WebauthnEnrollmentResponse | null = null;
    try {
      // 2. Initiate the WebAuthn enrollment with the backend.
      // Await the last value from the token service's enrollment call.
      webauthnEnrollmentResponse = await lastValueFrom(
        this.tokenService.enrollToken<
          WebAuthnEnrollmentData,
          WebauthnEnrollmentResponse
        >({
          data: webauthnEnrollmentData,
          mapper: this.enrollmentMapper,
        }),
      );
    } catch (error: any) {
      // Handle errors during the initial enrollment call to the backend.
      const errMsg = `WebAuthn registration process failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      // Return null to indicate failure and stop the enrollment process.
      return null;
    }

    // 3. Validate the initial enrollment response from the backend.
    // Ensure the response and its 'detail' property are present.
    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.openSnackBar(
        'Failed to initiate WebAuthn registration: Invalid server response or missing details.',
      );
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegOptions = detail?.webAuthnRegisterRequest;

    // Ensure the WebAuthn registration request options are available.
    if (!webAuthnRegOptions) {
      this.notificationService.openSnackBar(
        'Failed to initiate WebAuthn registration: Missing WebAuthn registration request data.',
      );
      return null;
    }

    // 4. Open the first step dialog to prompt the user for WebAuthn interaction.
    this.openStepOneDialog({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse,
    });

    // 5. Finalize the enrollment by interacting with the WebAuthn device.
    // This step must be awaited as it involves user interaction and credential creation.
    const responseLastStep = await this.finalizeEnrollment({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse,
    });

    // If finalization fails (returns null), close the dialog and indicate overall failure.
    if (!responseLastStep) {
      this.closeStepOneDialog(); // Ensure dialog is closed if finalization fails
      return null;
    }

    // On successful finalization, return the final enrollment response.
    return responseLastStep;
  };

  /**
   * Reads the public key credential from the WebAuthn device using `navigator.credentials.create`.
   * This function interacts with the browser's WebAuthn API based on server-provided options.
   * @param enrollmentResponse - The initial enrollment response containing WebAuthn registration request details.
   * @returns A Promise resolving to the PublicKeyCredential object on success, or null on failure/cancellation.
   */
  readPublicKeyCred = async (
    enrollmentResponse: WebauthnEnrollmentResponse,
  ): Promise<any | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;

    // Validate the request data.
    if (!request) {
      this.notificationService.openSnackBar(
        'Invalid WebAuthn registration request data.',
      );
      return null; // Handle the error gracefully
    }

    // Construct the publicKeyOptions object required by navigator.credentials.create.
    // Base64URL decoding is applied to challenge and excludeCredentials IDs.
    const publicKeyOptions: any = {
      rp: {
        id: request.relyingParty.id,
        name: request.relyingParty.name,
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber), // Serial number encoded as Uint8Array.
        name: request.name,
        displayName: request.displayName,
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce), // Challenge is a byte array.
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred: any) => ({
            id: this.base64Service.base64URLToBytes(cred.id),
            type: cred.type,
            transports: cred.transports,
          }))
        : [], // Convert excluded credential IDs from base64URL to bytes.
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation,
      extensions: request.extensions,
    };

    let publicKeyCred: any | null = null;
    try {
      // Attempt to create the public key credential using the WebAuthn API.
      publicKeyCred = await navigator.credentials.create({
        publicKey: publicKeyOptions,
      });
    } catch (browserOrCredentialError: any) {
      // Catch errors during credential creation (e.g., user cancels, device error).
      this.notificationService.openSnackBar(
        `WebAuthn credential creation failed: ${browserOrCredentialError.message || 'Unknown error'}`,
      );
      publicKeyCred = null; // Set to null on error
    } finally {
      // Ensure the dialog is closed regardless of success or failure in credential creation.
      this.closeStepOneDialog();
    }
    return publicKeyCred;
  };

  /**
   * Finalizes the WebAuthn enrollment by sending the created credential back to the backend.
   * @param args - An object containing webauthnEnrollmentData and webauthnEnrollmentResponse.
   * @returns A Promise resolving to EnrollmentResponse on success, or null on failure.
   */
  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;

    // Defensive check: Ensure enrollment response and its detail are valid.
    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.openSnackBar(
        'Enrollment response or its detail is missing for finalization.',
      );
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegisterRequest = detail?.webAuthnRegisterRequest;

    // Defensive check: Ensure necessary transaction details are present.
    if (
      !webAuthnRegisterRequest ||
      !webAuthnRegisterRequest.transaction_id ||
      !detail.serial
    ) {
      this.notificationService.openSnackBar(
        'Invalid transaction ID or serial number in enrollment detail for finalization.',
      );
      return null; // Return null on error
    }

    // Read the public key credential from the WebAuthn device.
    const publicKeyCred = await this.readPublicKeyCred(
      webauthnEnrollmentResponse,
    );
    if (publicKeyCred === null) {
      // If credential creation failed or was cancelled, readPublicKeyCred handles notifications,
      // so we just return null here to propagate the failure.
      return null;
    }

    // Prepare the parameters for the finalization call to the backend.
    // Convert ArrayBuffers from publicKeyCred.response to Base64 strings.
    const params: WebauthnFinalizeData = {
      ...webauthnEnrollmentData,
      transaction_id: webAuthnRegisterRequest.transaction_id,
      serial: detail.serial,
      credential_id: publicKeyCred.id, // Credential ID (might be ArrayBuffer)
      rawId: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.rawId), // Raw ID (ArrayBuffer)
      ),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      regdata: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.response.attestationObject), // Attestation object (ArrayBuffer)
      ),
      clientdata: this.base64Service.bytesToBase64(
        new Uint8Array(publicKeyCred.response.clientDataJSON), // Client data JSON (ArrayBuffer)
      ),
    };

    // Add client extension results if available.
    const extResults = publicKeyCred.getClientExtensionResults();
    if (extResults.credProps) {
      params.credProps = extResults.credProps;
    }

    try {
      // Send the finalization data to the backend.
      return await firstValueFrom(
        this.tokenService.enrollToken({
          data: params,
          mapper: this.enrollmentMapper,
        }),
      );
    } catch (error: any) {
      // Handle errors during the finalization call to the backend.
      const errMsg = `WebAuthn finalization failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      return null; // Return null on error
    }
  }

  /**
   * Opens the first step dialog for WebAuthn enrollment.
   * This dialog typically prompts the user to interact with their WebAuthn device.
   * @param args - Object containing enrollment data and response.
   */
  openStepOneDialog(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): void {
    const { webauthnEnrollmentResponse } = args;

    // Emit an event to allow the parent component to re-open this dialog if needed.
    // The emitted function will only open the dialog and return the response,
    // it will NOT trigger the finalization step directly from here.
    this.reopenCurrentEnrollmentDialogChange.emit(async () => {
      // Check if the dialog is already open to prevent multiple instances.
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen()) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { enrollmentResponse: webauthnEnrollmentResponse },
          disableClose: true,
        });
        return webauthnEnrollmentResponse;
      }
      return undefined;
    });

    // Open the dialog immediately when this function is called.
    this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse: webauthnEnrollmentResponse },
      disableClose: true,
    });
  }

  /**
   * Closes the first step dialog for WebAuthn enrollment.
   */
  closeStepOneDialog(): void {
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
