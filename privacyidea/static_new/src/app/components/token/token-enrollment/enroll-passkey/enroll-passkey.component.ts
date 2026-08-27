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
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  PasskeyApiPayloadMapper,
  PasskeyEnrollmentData,
  PasskeyFinalizeApiPayloadMapper,
  PasskeyFinalizeData
} from "@app/mappers/token-api-payload/passkey-token-api-payload.mapper";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import {
  TokenEnrollmentFirstStepDialogComponent,
  TokenEnrollmentFirstStepDialogData
} from "@components/token/token-enrollment/token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { lastValueFrom } from "rxjs";

@Component({
  selector: "app-enroll-passkey",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-passkey.component.html",
  styleUrl: "./enroll-passkey.component.scss",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollPasskeyComponent) }]
})
export class EnrollPasskeyComponent extends EnrollTokenBase<PasskeyEnrollmentData> {
  protected readonly enrollmentMapper: PasskeyApiPayloadMapper = inject(PasskeyApiPayloadMapper);
  protected readonly finalizeMapper: PasskeyFinalizeApiPayloadMapper = inject(PasskeyFinalizeApiPayloadMapper);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  currentStepOneRef?: MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  >;

  readonly registrationFailed = signal(false);

  buildEnrollmentArgs(basicEnrollmentData: TokenEnrollmentData): EnrollmentArgs<PasskeyEnrollmentData> | null {
    if (!navigator.credentials?.create) {
      const errorMsg = $localize`Passkey/WebAuthn is not supported by this browser.`;
      this.notificationService.error(errorMsg);
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
  }

  override async onEnrollmentResponse(
    enrollmentResponse: EnrollmentResponse,
    enrollmentInitData: TokenEnrollmentData
  ): Promise<EnrollmentStepResult> {
    if (enrollmentInitData.type !== "passkey") {
      console.warn("Received enrollment data is not of type 'passkey'. Cannot proceed with Passkey enrollment.");
      return null;
    }
    if (!enrollmentResponse.detail?.passkey_registration) {
      this.notificationService.error($localize`Failed to initiate Passkey registration: Invalid server response.`);
      throw new Error("Invalid server response for Passkey initiation.");
    }

    return this.runRegistration({
      enrollmentInitData: enrollmentInitData as PasskeyEnrollmentData,
      enrollmentResponse
    });
  }

  private async runRegistration(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
  }): Promise<EnrollmentStepResult> {
    const dialogRef = this.openStepOneDialog(args);
    void this.attemptRegistration(args);

    const dialogResult = await lastValueFrom(dialogRef.afterClosed());
    if (dialogResult === ENROLLMENT_CANCELLED) {
      this.reopenDialog.set(undefined);
      return ENROLLMENT_CANCELLED;
    }
    return dialogResult ?? null;
  }

  private async attemptRegistration(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
  }): Promise<void> {
    const dialogRef = this.currentStepOneRef;
    this.registrationFailed.set(false);

    const publicKeyCred = await this.readPublicKeyCred(args.enrollmentResponse);
    if (!publicKeyCred || (dialogRef && !this.dialogService.isDialogOpen(dialogRef))) {
      this.registrationFailed.set(true);
      return;
    }

    const responseLastStep = await this.finalizeEnrollment({ ...args, publicKeyCred }).catch(() => null);
    dialogRef?.close(responseLastStep ?? ENROLLMENT_CANCELLED);
  }

  openStepOneDialog(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
  }): MatDialogRef<
    AbstractDialogComponent<TokenEnrollmentFirstStepDialogData, EnrollmentStepResult>,
    EnrollmentStepResult
  > {
    const { enrollmentInitData, enrollmentResponse } = args;
    const canCancel = !enrollmentInitData.rollover && this.authService.actionAllowed("delete");

    this.reopenDialog.set(async () => {
      if (this.currentStepOneRef && this.dialogService.isDialogOpen(this.currentStepOneRef)) {
        return null;
      }
      return this.runRegistration(args);
    });

    this.currentStepOneRef = this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: {
        enrollmentResponse,
        showCancelButton: canCancel,
        showCloseButton: !canCancel,
        registrationFailed: this.registrationFailed.asReadonly(),
        onRetry: () => void this.attemptRegistration(args)
      }
    });
    return this.currentStepOneRef;
  }

  private async readPublicKeyCred(responseStepOne: EnrollmentResponse): Promise<PublicKeyCredential | null> {
    const detail = responseStepOne.detail;
    const passkeyRegOptions = detail?.passkey_registration;
    if (!passkeyRegOptions) {
      this.notificationService.error($localize`Failed to initiate Passkey registration: Invalid server response.`);
      return null;
    }
    const excludedCredentials = passkeyRegOptions.excludeCredentials.map((cred) => ({
      id: this.base64Service.base64URLToBytes(cred.id) as BufferSource,
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
        this.notificationService.error(
          $localize`Passkey credential creation failed: ${browserOrCredentialError.message}`
        );
        return null;
      });
    return publicKeyCred as PublicKeyCredential | null;
  }

  private async finalizeEnrollment(args: {
    enrollmentInitData: PasskeyEnrollmentData;
    enrollmentResponse: EnrollmentResponse;
    publicKeyCred: PublicKeyCredential;
  }): Promise<EnrollmentResponse> {
    const { enrollmentInitData, enrollmentResponse, publicKeyCred } = args;
    const detail = enrollmentResponse.detail;
    const attestationResponse = publicKeyCred.response as AuthenticatorAttestationResponse;
    const passkeyFinalizeData: PasskeyFinalizeData = {
      ...enrollmentInitData,
      transaction_id: detail["transaction_id"] as string,
      serial: detail.serial,
      credential_id: publicKeyCred.id,
      rawId: this.base64Service.bytesToBase64(new Uint8Array(publicKeyCred.rawId)),
      authenticatorAttachment: publicKeyCred.authenticatorAttachment,
      attestationObject: this.base64Service.bytesToBase64(new Uint8Array(attestationResponse.attestationObject)),
      clientDataJSON: this.base64Service.bytesToBase64(new Uint8Array(attestationResponse.clientDataJSON))
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
        this.notificationService.error(
          $localize`Error during final Passkey registration step. Attempting to clean up token.`
        );
        await lastValueFrom(this.tokenService.deleteToken(detail.serial)).catch(() => {
          this.notificationService.error(
            $localize`Failed to delete token ${detail.serial} after registration error. Please check manually.`
          );
          throw new Error(errorStep3);
        });
        this.notificationService.error($localize`Token ${detail.serial} deleted due to registration error.`);
        throw Error(errorStep3);
      })
      .then((finalResponse) => {
        this.reopenDialog.set(undefined);
        if (finalResponse.detail) {
          finalResponse.detail.serial = detail.serial;
        } else {
          finalResponse.detail = { serial: detail.serial } as EnrollmentResponseDetail;
        }
        return finalResponse;
      });
  }
}
