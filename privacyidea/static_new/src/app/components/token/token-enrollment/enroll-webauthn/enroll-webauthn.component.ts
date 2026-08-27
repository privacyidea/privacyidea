/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { Component, forwardRef, inject, signal } from "@angular/core";
import { MatDialogRef } from "@angular/material/dialog";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebauthnEnrollmentResponse,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnFinalizeData
} from "@app/mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import {
  TokenEnrollmentFirstStepDialogComponent,
  TokenEnrollmentFirstStepDialogData
} from "@components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { firstValueFrom, lastValueFrom } from "rxjs";

@Component({
  selector: "app-enroll-webauthn",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-webauthn.component.html",
  styleUrl: "./enroll-webauthn.component.scss",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollWebauthnComponent) }]
})
export class EnrollWebauthnComponent extends EnrollTokenBase<WebAuthnEnrollmentData> {
  protected readonly enrollmentMapper: WebAuthnApiPayloadMapper = inject(WebAuthnApiPayloadMapper);
  protected readonly finalizeMapper: WebAuthnFinalizeApiPayloadMapper = inject(WebAuthnFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  stepOneDialogRef: MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  > | null = null;

  readonly registrationFailed = signal(false);

  buildEnrollmentArgs(basicEnrollmentData: TokenEnrollmentData): EnrollmentArgs<WebAuthnEnrollmentData> | null {
    if (!navigator.credentials?.create) {
      const errorMsg = $localize`WebAuthn is not supported by this browser.`;
      this.notificationService.error(errorMsg);
      return null;
    }

    const webauthnEnrollmentData: WebAuthnEnrollmentData = {
      ...basicEnrollmentData,
      type: "webauthn"
    };

    return {
      data: webauthnEnrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  override async onEnrollmentResponse(
    enrollmentResponse: EnrollmentResponse,
    enrollmentData: TokenEnrollmentData
  ): Promise<EnrollmentStepResult> {
    if (!enrollmentResponse?.detail) {
      this.notificationService.error(
        $localize`Failed to initiate WebAuthn registration: Invalid server response or missing details.`
      );
      return null;
    } else if (!enrollmentResponse?.detail?.["webAuthnRegisterRequest"]) {
      this.notificationService.error(
        $localize`Failed to initiate WebAuthn registration: Missing WebAuthn registration request data.`
      );
      return null;
    } else if (enrollmentData.type !== "webauthn") {
      console.warn("Received enrollment data is not of type 'webauthn'. Cannot proceed with WebAuthn enrollment.");
      return null;
    }

    const webauthnEnrollmentResponse = enrollmentResponse as WebauthnEnrollmentResponse;
    const registerRequest = webauthnEnrollmentResponse.detail.webAuthnRegisterRequest;
    if (!registerRequest?.transaction_id || !webauthnEnrollmentResponse.detail.serial) {
      this.notificationService.warning(
        $localize`Invalid transaction ID or serial number in enrollment detail for finalization.`
      );
      return null;
    }

    return this.runRegistration({
      webauthnEnrollmentData: enrollmentData as WebAuthnEnrollmentData,
      webauthnEnrollmentResponse
    });
  }

  private async runRegistration(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): Promise<EnrollmentStepResult> {
    const dialogRef = this.openStepOneDialog(args);
    const dialogClosed = lastValueFrom(dialogRef.afterClosed());
    void this.attemptRegistration(args);

    const dialogResult = await dialogClosed;
    if (dialogResult === ENROLLMENT_CANCELLED) {
      this.reopenDialog.set(undefined);
      return ENROLLMENT_CANCELLED;
    }
    return dialogResult ?? null;
  }

  private async attemptRegistration(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): Promise<void> {
    const dialogRef = this.stepOneDialogRef;
    this.registrationFailed.set(false);

    const publicKeyCred = await this.readPublicKeyCred(args.webauthnEnrollmentResponse);
    if (!publicKeyCred || (dialogRef && !this.dialogService.isDialogOpen(dialogRef))) {
      this.registrationFailed.set(true);
      return;
    }

    const responseLastStep = await this.finalizeEnrollment({ ...args, publicKeyCred });
    if (!responseLastStep) {
      this.registrationFailed.set(true);
      return;
    }
    dialogRef?.close(responseLastStep);
  }

  readPublicKeyCred = async (enrollmentResponse: WebauthnEnrollmentResponse): Promise<PublicKeyCredential | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;

    if (!request) {
      this.notificationService.warning($localize`Invalid WebAuthn registration request data.`);
      return null;
    }

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: {
        id: request.relyingParty.id,
        name: request.relyingParty.name
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber) as BufferSource,
        name: request.name,
        displayName: request.displayName
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce) as BufferSource,
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred) => ({
            id: this.base64Service.base64URLToBytes(cred.id) as BufferSource,
            type: cred.type as PublicKeyCredentialType,
            transports: cred.transports as AuthenticatorTransport[] | undefined
          }))
        : [],
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation as AttestationConveyancePreference,
      extensions: request.extensions
    };

    let publicKeyCred: PublicKeyCredential | null;
    try {
      publicKeyCred = (await navigator.credentials.create({
        publicKey: publicKeyOptions
      })) as PublicKeyCredential | null;
    } catch (browserOrCredentialError) {
      const message =
        browserOrCredentialError instanceof Error ? browserOrCredentialError.message : String(browserOrCredentialError);
      this.notificationService.error($localize`WebAuthn credential creation failed: ${message || "Unknown error"}`);
      publicKeyCred = null;
    }
    return publicKeyCred;
  };

  openStepOneDialog(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  > {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;
    const canCancel = !webauthnEnrollmentData.rollover && this.authService.actionAllowed("delete");

    this.reopenDialog.set(async () => {
      if (this.stepOneDialogRef && this.dialogService.isDialogOpen(this.stepOneDialogRef)) {
        return null;
      }
      return this.runRegistration(args);
    });

    this.stepOneDialogRef = this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: {
        enrollmentResponse: webauthnEnrollmentResponse,
        showCancelButton: canCancel,
        showCloseButton: !canCancel,
        registrationFailed: this.registrationFailed.asReadonly(),
        onRetry: () => void this.attemptRegistration(args)
      }
    });
    return this.stepOneDialogRef;
  }

  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
    publicKeyCred: PublicKeyCredential;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse, publicKeyCred } = args;

    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.warning($localize`Enrollment response or its detail is missing for finalization.`);
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegisterRequest = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegisterRequest || !webAuthnRegisterRequest.transaction_id || !detail.serial) {
      this.notificationService.warning(
        $localize`Invalid transaction ID or serial number in enrollment detail for finalization.`
      );
      return null;
    }

    const attestationResponse = publicKeyCred.response as AuthenticatorAttestationResponse;
    const params: WebauthnFinalizeData = {
      ...webauthnEnrollmentData,
      transaction_id: webAuthnRegisterRequest.transaction_id,
      serial: detail.serial,
      credential_id: publicKeyCred.id,
      rawId: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.rawId)),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      regdata: this.base64Service.bytesToBase64(new Uint8Array(attestationResponse.attestationObject)),
      clientdata: this.base64Service.bytesToBase64(new Uint8Array(attestationResponse.clientDataJSON))
    };

    const extResults = publicKeyCred.getClientExtensionResults();
    if (extResults.credProps) {
      params.credProps = extResults.credProps;
    }

    try {
      const response: EnrollmentResponse = await firstValueFrom(
        this.tokenService.enrollToken({
          data: params,
          mapper: this.finalizeMapper
        })
      );
      response.detail.serial = detail.serial;
      return { ...response };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const errMsg = $localize`WebAuthn finalization failed: ${message || error}`;
      this.notificationService.error(errMsg);
      return null;
    }
  }
}
