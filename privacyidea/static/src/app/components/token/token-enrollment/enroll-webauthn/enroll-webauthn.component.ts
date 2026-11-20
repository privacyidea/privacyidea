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

import { Component, forwardRef, inject } from "@angular/core";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebauthnEnrollmentResponse,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnFinalizeData
} from "@app/mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import type { EnrollmentFirstStep } from "@components/token/token-enrollment/enrollment-flow";
import { EnrollmentStepResult } from "@components/token/token-enrollment/token-enrollment.constants";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { firstValueFrom } from "rxjs";

@Component({
  selector: "app-enroll-webauthn",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-webauthn.component.html",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollWebauthnComponent) }]
})
export class EnrollWebauthnComponent extends EnrollTokenBase<WebAuthnEnrollmentData> {
  protected readonly enrollmentMapper: WebAuthnApiPayloadMapper = inject(WebAuthnApiPayloadMapper);
  protected readonly finalizeMapper: WebAuthnFinalizeApiPayloadMapper = inject(WebAuthnFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);

  buildEnrollmentArgs(basicEnrollmentData: TokenEnrollmentData): EnrollmentArgs<WebAuthnEnrollmentData> | null {
    if (!navigator.credentials?.create) {
      const errorMsg = $localize`:@@token.webauthnNotSupported:WebAuthn is not supported by this browser.`;
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

  override firstStep(enrollmentResponse: EnrollmentResponse, enrollmentData: TokenEnrollmentData): EnrollmentFirstStep {
    return { kind: "fido2", register: (signal) => this.register(enrollmentResponse, enrollmentData, signal) };
  }

  private async register(
    enrollmentResponse: EnrollmentResponse,
    enrollmentData: TokenEnrollmentData,
    signal: AbortSignal
  ): Promise<EnrollmentStepResult> {
    if (!enrollmentResponse?.detail) {
      this.notificationService.error(
        $localize`:@@token.failedInitiateWebauthn:Failed to initiate WebAuthn registration: Invalid server response or missing details.`
      );
      return null;
    } else if (!enrollmentResponse?.detail?.["webAuthnRegisterRequest"]) {
      this.notificationService.error(
        $localize`:@@token.failedInitiateWebauthnRegistration:Failed to initiate WebAuthn registration: Missing WebAuthn registration request data.`
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
        $localize`:@@token.invalidTransaction:Invalid transaction ID or serial number in enrollment detail for finalization.`
      );
      return null;
    }

    const publicKeyCred = await this.readPublicKeyCred(webauthnEnrollmentResponse);
    if (!publicKeyCred || signal.aborted) {
      return null;
    }
    return this.finalizeEnrollment({
      webauthnEnrollmentData: enrollmentData as WebAuthnEnrollmentData,
      webauthnEnrollmentResponse,
      publicKeyCred
    });
  }

  readPublicKeyCred = async (enrollmentResponse: WebauthnEnrollmentResponse): Promise<PublicKeyCredential | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;

    if (!request) {
      this.notificationService.warning($localize`:@@token.invalidWebauthn:Invalid WebAuthn registration request data.`);
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
      this.notificationService.error(
        $localize`:@@token.webauthnCredential:WebAuthn credential creation failed: ${message || "Unknown error"}:MESSAGE:`
      );
      publicKeyCred = null;
    }
    return publicKeyCred;
  };

  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
    publicKeyCred: PublicKeyCredential;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse, publicKeyCred } = args;

    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.warning(
        $localize`:@@token.enrollmentResponse:Enrollment response or its detail is missing for finalization.`
      );
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegisterRequest = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegisterRequest || !webAuthnRegisterRequest.transaction_id || !detail.serial) {
      this.notificationService.warning(
        $localize`:@@token.invalidTransaction:Invalid transaction ID or serial number in enrollment detail for finalization.`
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
      const errMsg = $localize`:@@token.webauthnFinalization:WebAuthn finalization failed: ${message || error}:MESSAGE:`;
      this.notificationService.error(errMsg);
      return null;
    }
  }
}
