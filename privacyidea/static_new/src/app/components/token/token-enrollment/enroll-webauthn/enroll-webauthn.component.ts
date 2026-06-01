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

import { Component, EventEmitter, inject, Input, OnInit, Output } from "@angular/core";
import { MatDialogRef } from "@angular/material/dialog";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebauthnEnrollmentResponse,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnFinalizeData
} from "@app/mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { TokenEnrollmentFirstStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import { ReopenDialogFn } from "@components/token/token-enrollment/token-enrollment.component";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { firstValueFrom } from "rxjs";

@Component({
  selector: "app-enroll-webauthn",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-webauthn.component.html",
  styleUrl: "./enroll-webauthn.component.scss"
})
export class EnrollWebauthnComponent implements OnInit {
  protected readonly enrollmentMapper = inject(WebAuthnApiPayloadMapper);
  protected readonly finalizeMapper = inject(WebAuthnFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  @Input() wizard = false;
  @Output() additionalFormFieldsChange = new EventEmitter<Record<string, unknown>>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: WebAuthnEnrollmentData;
      mapper: TokenApiPayloadMapper<WebAuthnEnrollmentData>;
    } | null
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();
  @Output() enrollmentResponseChange = new EventEmitter<
    (enrollmentResponse: EnrollmentResponse, enrollmentData: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this.enrollmentResponseChange.emit(this.onEnrollmentResponse.bind(this));
  }

  enrollmentArgsGetter = (
    basicEnrollmentData: TokenEnrollmentData
  ): {
    data: WebAuthnEnrollmentData;
    mapper: TokenApiPayloadMapper<WebAuthnEnrollmentData>;
  } | null => {
    if (!navigator.credentials?.create) {
      const errorMsg = "WebAuthn is not supported by this browser.";
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
  };

  async onEnrollmentResponse(
    enrollmentResponse: EnrollmentResponse,
    enrollmentData: TokenEnrollmentData
  ): Promise<EnrollmentResponse | null> {
    if (!(enrollmentResponse as WebauthnEnrollmentResponse)?.detail) {
      this.notificationService.error(
        "Failed to initiate WebAuthn registration: Invalid server response or missing details."
      );
      return null;
    } else if (!(enrollmentResponse as WebauthnEnrollmentResponse)?.detail?.webAuthnRegisterRequest) {
      this.notificationService.error(
        "Failed to initiate WebAuthn registration: Missing WebAuthn registration request data."
      );
      return null;
    } else if (enrollmentData.type !== "webauthn") {
      console.warn("Received enrollment data is not of type 'webauthn'. Cannot proceed with WebAuthn enrollment.");
      return null;
    }
    const webauthnEnrollmentResponse = enrollmentResponse as WebauthnEnrollmentResponse;
    const webauthnEnrollmentData = enrollmentData as WebAuthnEnrollmentData;

    this.openStepOneDialog({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse
    });

    const responseLastStep = await this.finalizeEnrollment({
      webauthnEnrollmentData,
      webauthnEnrollmentResponse: webauthnEnrollmentResponse
    });

    if (!responseLastStep) {
      this.closeStepOneDialog();
      return null;
    }

    return responseLastStep;
  }

  readPublicKeyCred = async (enrollmentResponse: WebauthnEnrollmentResponse): Promise<PublicKeyCredential | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;

    if (!request) {
      this.notificationService.warning("Invalid WebAuthn registration request data.");
      return null;
    }

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: {
        id: request.relyingParty.id,
        name: request.relyingParty.name
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber),
        name: request.name,
        displayName: request.displayName
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce).buffer as ArrayBuffer,
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred) => ({
            id: this.base64Service.base64URLToBytes(cred.id).buffer as ArrayBuffer,
            type: cred.type as PublicKeyCredentialType,
            transports: cred.transports as AuthenticatorTransport[] | undefined
          }))
        : [],
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation as AttestationConveyancePreference | undefined,
      extensions: request.extensions
    };

    let publicKeyCred: PublicKeyCredential | null = null;
    try {
      publicKeyCred = (await navigator.credentials.create({
        publicKey: publicKeyOptions
      })) as PublicKeyCredential | null;
    } catch (browserOrCredentialError) {
      const message = browserOrCredentialError instanceof Error ? browserOrCredentialError.message : "Unknown error";
      this.notificationService.error(`WebAuthn credential creation failed: ${message}`);
    } finally {
      this.closeStepOneDialog();
    }
    return publicKeyCred;
  };

  stepOneDialogRef: MatDialogRef<AbstractDialogComponent, boolean> | null = null;

  openStepOneDialog(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): void {
    const { webauthnEnrollmentResponse } = args;

    this.reopenDialogChange.emit(async () => {
      if (this.stepOneDialogRef && this.dialogService.isDialogOpen(this.stepOneDialogRef)) {
        return null;
      }
      this.stepOneDialogRef = this.dialogService.openDialog({
        component: TokenEnrollmentFirstStepDialogComponent,
        data: { enrollmentResponse: webauthnEnrollmentResponse }
      });

      return null;
    });
    this.stepOneDialogRef = this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: { enrollmentResponse: webauthnEnrollmentResponse }
    });
  }

  closeStepOneDialog(): void {
    if (this.stepOneDialogRef) {
      this.stepOneDialogRef.close(true);
      this.stepOneDialogRef = null;
    }
  }

  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;

    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.warning("Enrollment response or its detail is missing for finalization.");
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegisterRequest = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegisterRequest || !webAuthnRegisterRequest.transaction_id || !detail.serial) {
      this.notificationService.warning(
        "Invalid transaction ID or serial number in enrollment detail for finalization."
      );
      return null;
    }

    const publicKeyCred = await this.readPublicKeyCred(webauthnEnrollmentResponse);
    if (publicKeyCred === null) {
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
      this.notificationService.error(`WebAuthn finalization failed: ${message}`);
      return null;
    }
  }
}
