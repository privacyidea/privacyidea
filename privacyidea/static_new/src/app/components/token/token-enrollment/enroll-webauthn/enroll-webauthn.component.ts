/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { firstValueFrom, from, lastValueFrom, Observable } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  WebAuthnApiPayloadMapper,
  WebAuthnEnrollmentData,
  WebauthnEnrollmentResponse,
  WebAuthnFinalizeApiPayloadMapper,
  WebauthnFinalizeData
} from "../../../../mappers/token-api-payload/webauthn-token-api-payload.mapper";
import { Base64Service, Base64ServiceInterface } from "../../../../services/base64/base64.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ReopenDialogFn } from "../token-enrollment.component";

@Component({
  selector: "app-enroll-webauthn",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-webauthn.component.html",
  styleUrl: "./enroll-webauthn.component.scss"
})
export class EnrollWebauthnComponent implements OnInit {
  protected readonly enrollmentMapper: WebAuthnApiPayloadMapper = inject(WebAuthnApiPayloadMapper);
  protected readonly finalizeMapper: WebAuthnFinalizeApiPayloadMapper = inject(WebAuthnFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();

  webauthnForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit((data) => from(this.onClickEnroll(data)));
  }

  onClickEnroll = async (basicEnrollmentData: TokenEnrollmentData): Promise<EnrollmentResponse | null> => {
    if (!navigator.credentials?.create) {
      const errorMsg = "WebAuthn is not supported by this browser.";
      this.notificationService.openSnackBar(errorMsg);
      return null;
    }

    const webauthnEnrollmentData: WebAuthnEnrollmentData = {
      ...basicEnrollmentData,
      type: "webauthn"
    };

    let webauthnEnrollmentResponse: WebauthnEnrollmentResponse | null = null;
    try {
      webauthnEnrollmentResponse = await lastValueFrom(
        this.tokenService.enrollToken<WebAuthnEnrollmentData, WebauthnEnrollmentResponse>({
          data: webauthnEnrollmentData,
          mapper: this.enrollmentMapper
        })
      );
    } catch (error: any) {
      const errMsg = `WebAuthn registration process failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      return null;
    }

    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.openSnackBar(
        "Failed to initiate WebAuthn registration: Invalid server response or missing details."
      );
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegOptions = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegOptions) {
      this.notificationService.openSnackBar(
        "Failed to initiate WebAuthn registration: Missing WebAuthn registration request data."
      );
      return null;
    }

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
  };

  readPublicKeyCred = async (enrollmentResponse: WebauthnEnrollmentResponse): Promise<any | null> => {
    const request = enrollmentResponse.detail?.webAuthnRegisterRequest;

    if (!request) {
      this.notificationService.openSnackBar("Invalid WebAuthn registration request data.");
      return null;
    }

    const publicKeyOptions: any = {
      rp: {
        id: request.relyingParty.id,
        name: request.relyingParty.name
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber),
        name: request.name,
        displayName: request.displayName
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce),
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred: any) => ({
          id: this.base64Service.base64URLToBytes(cred.id),
          type: cred.type,
          transports: cred.transports
        }))
        : [],
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation,
      extensions: request.extensions
    };

    let publicKeyCred: any | null = null;
    try {
      publicKeyCred = await navigator.credentials.create({
        publicKey: publicKeyOptions
      });
    } catch (browserOrCredentialError: any) {
      this.notificationService.openSnackBar(
        `WebAuthn credential creation failed: ${browserOrCredentialError.message || "Unknown error"}`
      );
      publicKeyCred = null;
    } finally {
      this.closeStepOneDialog();
    }
    return publicKeyCred;
  };

  openStepOneDialog(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): void {
    const { webauthnEnrollmentResponse } = args;

    this.reopenDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { enrollmentResponse: webauthnEnrollmentResponse },
          disableClose: true
        });
        return webauthnEnrollmentResponse;
      }
      return null;
    });

    this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse: webauthnEnrollmentResponse },
      disableClose: true
    });
  }

  closeStepOneDialog(): void {
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }

  private async finalizeEnrollment(args: {
    webauthnEnrollmentData: WebAuthnEnrollmentData;
    webauthnEnrollmentResponse: WebauthnEnrollmentResponse;
  }): Promise<EnrollmentResponse | null> {
    const { webauthnEnrollmentData, webauthnEnrollmentResponse } = args;

    if (!webauthnEnrollmentResponse || !webauthnEnrollmentResponse.detail) {
      this.notificationService.openSnackBar("Enrollment response or its detail is missing for finalization.");
      return null;
    }

    const detail = webauthnEnrollmentResponse.detail;
    const webAuthnRegisterRequest = detail?.webAuthnRegisterRequest;

    if (!webAuthnRegisterRequest || !webAuthnRegisterRequest.transaction_id || !detail.serial) {
      this.notificationService.openSnackBar(
        "Invalid transaction ID or serial number in enrollment detail for finalization."
      );
      return null;
    }

    const publicKeyCred = await this.readPublicKeyCred(webauthnEnrollmentResponse);
    if (publicKeyCred === null) {
      return null;
    }

    const params: WebauthnFinalizeData = {
      ...webauthnEnrollmentData,
      transaction_id: webAuthnRegisterRequest.transaction_id,
      serial: detail.serial,
      credential_id: publicKeyCred.id,
      rawId: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.rawId)),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      regdata: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.response.attestationObject)),
      clientdata: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.response.clientDataJSON))
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
      return response;
    } catch (error: any) {
      const errMsg = `WebAuthn finalization failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      return null;
    }
  }
}
