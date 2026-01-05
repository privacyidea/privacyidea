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
import { Component, EventEmitter, inject, Input, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatDialogRef } from "@angular/material/dialog";
import { lastValueFrom } from "rxjs";
import {
  PasskeyApiPayloadMapper,
  PasskeyEnrollmentData,
  PasskeyFinalizeApiPayloadMapper,
  PasskeyFinalizeData
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
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";

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

  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: PasskeyEnrollmentData;
      mapper: TokenApiPayloadMapper<PasskeyEnrollmentData>;
    } | null
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();
  @Output() onEnrollmentResponseChange = new EventEmitter<
    (enrollmentResponse: EnrollmentResponse, enrollmentData: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();

  passkeyForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this.onEnrollmentResponseChange.emit(this.onEnrollmentResponse.bind(this));
  }

  enrollmentArgsGetter = (
    basicEnrollmentData: TokenEnrollmentData
  ): {
    data: PasskeyEnrollmentData;
    mapper: TokenApiPayloadMapper<PasskeyEnrollmentData>;
  } | null => {
    if (!navigator.credentials?.create) {
      const errorMsg = "Passkey/WebAuthn is not supported by this browser.";
      this.notificationService.openSnackBar(errorMsg);
      throw new Error(errorMsg);
    }

    const enrollmentInitData: PasskeyEnrollmentData = {
      ...basicEnrollmentData,
      type: "passkey"
    };

    return {
      data: enrollmentInitData,
      mapper: this.enrollmentMapper
    };
  };

  async onEnrollmentResponse(
    enrollmentResponse: EnrollmentResponse,
    enrollmentInitData: TokenEnrollmentData
  ): Promise<EnrollmentResponse | null> {
    let passkeyEnrollmentInitData: PasskeyEnrollmentData;
    if (enrollmentInitData.type !== "passkey") {
      console.warn("Received enrollment data is not of type 'passkey'. Cannot proceed with Passkey enrollment.");
      return null;
    } else {
      passkeyEnrollmentInitData = enrollmentInitData as PasskeyEnrollmentData;
    }
    const detail = enrollmentResponse.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.openSnackBar("Failed to initiate Passkey registration: Invalid server response.");
      throw new Error("Invalid server response for Passkey initiation.");
    }
    this.openStepOneDialog({
      enrollmentInitData: passkeyEnrollmentInitData as PasskeyEnrollmentData,
      enrollmentResponse
    });
    const publicKeyCred = await this.readPublicKeyCred(enrollmentResponse);
    if (publicKeyCred === null) {
      return null;
    }
    const resposeLastStep = await this.finalizeEnrollment({
      enrollmentInitData: passkeyEnrollmentInitData as PasskeyEnrollmentData,
      enrollmentResponse,
      publicKeyCred
    });
    return resposeLastStep;
  }

  currentStepOneRef?: MatDialogRef<
    {
      enrollmentResponse: EnrollmentResponse<EnrollmentResponseDetail>;
    },
    void
  >;

  openStepOneDialog(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
  }): MatDialogRef<
    {
      enrollmentResponse: EnrollmentResponse<EnrollmentResponseDetail>;
    },
    void
  > {
    const { enrollmentInitData, enrollmentResponse } = args;

    this.reopenDialogChange.emit(async () => {
      if (this.currentStepOneRef && this.dialogService.isDialogOpen(this.currentStepOneRef)) {
        return null;
      }
      this.currentStepOneRef = this.dialogService.openDialog({
        component: TokenEnrollmentFirstStepDialogComponent,
        data: { enrollmentResponse }
      });
      const publicKeyCred = await this.readPublicKeyCred(enrollmentResponse);
      const resposeLastStep = await this.finalizeEnrollment({
        enrollmentInitData,
        enrollmentResponse,
        publicKeyCred
      });
      return resposeLastStep;
    });

    this.currentStepOneRef = this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: { enrollmentResponse }
    });
    return this.currentStepOneRef;
  }

  closeStepOneDialog(): void {
    this.currentStepOneRef?.close();
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
        id: this.base64Service.base64URLToBytes(passkeyRegOptions.user.id) as BufferSource,
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
