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
import { MatDialogRef } from "@angular/material/dialog";
import { lastValueFrom } from "rxjs";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  PasskeyApiPayloadMapper,
  PasskeyFinalizeApiPayloadMapper
} from "../../../../mappers/token-api-payload/passkey-token-api-payload.mapper";
import { Base64Service, Base64ServiceInterface } from "../../../../services/base64/base64.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { TokenEnrollmentFirstStepDialogComponent } from "../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import { ReopenDialogFn } from "../token-enrollment.component";

export interface PasskeyEnrollmentData extends TokenEnrollmentData {
  type: "passkey";
}

export interface PasskeyFinalizeData extends PasskeyEnrollmentData {
  transaction_id: string;
  serial: string;
  credential_id: string;
  rawId: string;
  authenticatorAttachment: string | null;
  attestationObject: string;
  clientDataJSON: string;
  credProps?: any;
}

export interface PasskeyRegistrationParams {
  type: "passkey";
  transaction_id: string;
  serial: string;
  credential_id: string;
  rawId: string;
  authenticatorAttachment: string | null;
  attestationObject: string;
  clientDataJSON: string;
  credProps?: any;
}

@Component({
  selector: "app-enroll-passkey",
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule],
  templateUrl: "./enroll-passkey.component.html",
  styleUrl: "./enroll-passkey.component.scss"
})
export class EnrollPasskeyComponent implements OnInit {
  protected readonly enrollmentMapper: PasskeyApiPayloadMapper = inject(PasskeyApiPayloadMapper);
  protected readonly finalizeMapper: PasskeyFinalizeApiPayloadMapper = inject(PasskeyFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();

  passkeyForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = async (basicEnrollmentData: TokenEnrollmentData): Promise<EnrollmentResponse | null> => {
    if (!navigator.credentials?.create) {
      const errorMsg = "Passkey/WebAuthn is not supported by this browser.";
      this.notificationService.openSnackBar(errorMsg);
      throw new Error(errorMsg);
    }

    const enrollmentInitData: PasskeyEnrollmentData = {
      ...basicEnrollmentData,
      type: "passkey"
    };

    const enrollmentResponse = await lastValueFrom(
      this.tokenService.enrollToken({
        data: enrollmentInitData,
        mapper: this.enrollmentMapper
      })
    ).catch((error: any) => {
      const errMsg = `Passkey registration process failed: ${error.message || error}`;
      this.notificationService.openSnackBar(errMsg);
      throw new Error(errMsg);
    });

    const detail = enrollmentResponse.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.openSnackBar("Failed to initiate Passkey registration: Invalid server response.");
      throw new Error("Invalid server response for Passkey initiation.");
    }
    this.openStepOneDialog({ enrollmentInitData, enrollmentResponse });
    const publicKeyCred = await this.readPublicKeyCred(enrollmentResponse);
    if (publicKeyCred === null) {
      return null;
    }
    const resposeLastStep = await this.finalizeEnrollment({
      enrollmentInitData,
      enrollmentResponse,
      publicKeyCred
    });
    return resposeLastStep;
  };

  openStepOneDialog(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
  }): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    const { enrollmentInitData, enrollmentResponse } = args;
    this.reopenDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen) {
        this.dialogService.openTokenEnrollmentFirstStepDialog({
          data: { enrollmentResponse },
          disableClose: true
        });
        const publicKeyCred = await this.readPublicKeyCred(enrollmentResponse);
        const resposeLastStep = await this.finalizeEnrollment({
          enrollmentInitData,
          enrollmentResponse,
          publicKeyCred
        });
        return resposeLastStep;
      }
      return null;
    });

    return this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse },
      disableClose: true
    });
  }

  closeStepOneDialog(): void {
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }

  private async readPublicKeyCred(responseStepOne: EnrollmentResponse): Promise<any | null> {
    const detail = responseStepOne.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.openSnackBar("Failed to initiate Passkey registration: Invalid server response.");
      return null;
    }
    const excludedCredentials = passkeyRegOptions.excludeCredentials.map((cred: any) => ({
      id: this.base64Service.base64URLToBytes(cred.id),
      type: cred.type
    }));

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: passkeyRegOptions.rp,
      user: {
        id: this.base64Service.base64URLToBytes(passkeyRegOptions.user.id),
        name: passkeyRegOptions.user.name,
        displayName: passkeyRegOptions.user.displayName
      },
      challenge: new Uint8Array(new TextEncoder().encode(passkeyRegOptions.challenge)),
      pubKeyCredParams: passkeyRegOptions.pubKeyCredParams,
      excludeCredentials: excludedCredentials,
      authenticatorSelection: passkeyRegOptions.authenticatorSelection,
      timeout: passkeyRegOptions.timeout,
      extensions: { credProps: true, ...passkeyRegOptions.extensions },
      attestation: passkeyRegOptions.attestation
    };
    const publicKeyCred = await navigator.credentials
      .create({ publicKey: publicKeyOptions })
      .catch((browserOrCredentialError) => {
        this.notificationService.openSnackBar(
          `Passkey credential creation failed: ${browserOrCredentialError.message}`
        );
        return null;
      })
      .finally(() => {
        this.closeStepOneDialog();
      });
    return publicKeyCred;
  }

  private async finalizeEnrollment(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
    publicKeyCred: any;
  }): Promise<EnrollmentResponse> {
    const { enrollmentInitData, enrollmentResponse, publicKeyCred } = args;
    const detail = enrollmentResponse.detail;
    const passkeyFinalizeData: PasskeyFinalizeData = {
      ...enrollmentInitData,
      transaction_id: detail["transaction_id"]!,
      serial: detail.serial,
      credential_id: publicKeyCred.id,
      rawId: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.rawId)),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      attestationObject: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.response.attestationObject)),
      clientDataJSON: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.response.clientDataJSON))
    };

    const extResults = publicKeyCred.getClientExtensionResults();
    if (extResults?.credProps) {
      passkeyFinalizeData.credProps = extResults.credProps;
    }
    return lastValueFrom(
      this.tokenService.enrollToken({
        data: passkeyFinalizeData,
        mapper: this.finalizeMapper
      })
    )
      .catch(async (errorStep3) => {
        this.notificationService.openSnackBar(
          "Error during final Passkey registration step. Attempting to clean up token."
        );
        await lastValueFrom(this.tokenService.deleteToken(detail.serial)).catch(() => {
          this.notificationService.openSnackBar(
            `Failed to delete token ${detail.serial} after registration error. Please check manually.`
          );
          throw new Error(errorStep3);
        }),
          this.notificationService.openSnackBar(`Token ${detail.serial} deleted due to registration error.`);
        throw Error(errorStep3);
      })
      .then((finalResponse) => {
        this.reopenDialogChange.emit(undefined);
        if (finalResponse.detail) {
          finalResponse.detail.serial = detail.serial;
        } else {
          finalResponse.detail = { serial: detail.serial } as EnrollmentResponseDetail;
        }
        return finalResponse;
      });
  }
}
