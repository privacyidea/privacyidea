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

import { Component, WritableSignal, computed, inject, signal, viewChild } from "@angular/core";
import { form, FormField, required, validate, ValidationError } from "@angular/forms/signals";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { getTokenApiPayloadMapper } from "@app/mappers/token-api-payload/token-api-payload-mapper-registry";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import {
  EnrollmentPoliciesLoad,
  enrollmentPolicyState,
  loadEnrollmentPolicies
} from "@components/token/token-enrollment/enrollment-policy-values";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import {
  ENROLLMENT_CANCELLED,
  NO_DISMISS_LAST_STEP_TOKEN_TYPES
} from "@components/token/token-enrollment/token-enrollment.constants";
import { DialogAction } from "@models/dialog";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import {
  EnrollmentPolicyState,
  EnrollmentPolicyTarget,
  TokenDetails,
  TokenEnrollmentDialogData,
  TokenService,
  TokenServiceInterface
} from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { toObservable, toSignal } from "@angular/core/rxjs-interop";
import { Observable, lastValueFrom, of, switchMap } from "rxjs";

@Component({
  selector: "app-token-rollover",
  imports: [
    DialogWrapperComponent,
    EnrollTokenTypeSwitchComponent,
    FormField,
    MatError,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel
  ],
  standalone: true,
  templateUrl: "./token-rollover.component.html"
})
export class TokenRolloverComponent extends AbstractDialogComponent<
  {
    token: TokenDetails;
  },
  boolean
> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  token: WritableSignal<TokenEnrollmentData | null> = signal(null);
  title = computed(() => $localize`:@@token.rolloverToken:Rollover Token ${this.token()?.serial || ""}:SERIAL:`);
  serial = signal<string | null | undefined>(null);
  enrolledDialogData: WritableSignal<TokenEnrollmentDialogData | null> = signal(null);

  /** The target the enrollment policies are evaluated for, as POST /token/init sees it for the rollover. */
  private readonly enrollmentTarget = computed<EnrollmentPolicyTarget | undefined>(() => {
    const token = this.token();
    return token?.serial ? { type: token.type, serial: token.serial } : undefined;
  });

  private readonly enrollmentPoliciesLoad = toSignal(
    toObservable(this.enrollmentTarget).pipe(
      switchMap(
        (target): Observable<EnrollmentPoliciesLoad> =>
          target ? loadEnrollmentPolicies(this.tokenService.getEnrollmentPolicies(target)) : of({ status: "idle" })
      )
    ),
    { initialValue: { status: "idle" } as EnrollmentPoliciesLoad }
  );

  readonly enrollmentPolicyState = computed<EnrollmentPolicyState>(() =>
    enrollmentPolicyState(this.enrollmentPoliciesLoad())
  );

  /** The server message when the enrollment policies cannot be determined for the token, else null. */
  readonly enrollmentPoliciesError = computed<string | null>(() => {
    const load = this.enrollmentPoliciesLoad();
    return load.status === "error" ? load.message : null;
  });

  /** The description field is offered only when the policies require a description and the token has none. */
  readonly needsDescriptionInput = computed(() => {
    const state = this.enrollmentPolicyState();
    return state.state === "loaded" && !!state.policies.require_description && !this.token()?.description;
  });

  readonly description = signal("");
  readonly descriptionForm = form(this.description, (f) => {
    required(f, { when: () => this.needsDescriptionInput() });
    validate(f, (ctx) => {
      const v = ctx.value();
      const errors: ValidationError[] = [];
      if (this.needsDescriptionInput() && v !== "" && !v.trim()) errors.push({ kind: "required" });
      if (v.length > this.tokenService.maxDescriptionLength) errors.push({ kind: "maxlength" });
      return errors;
    });
  });

  readonly descriptionInvalid = computed(() => this.needsDescriptionInput() && !this.descriptionForm().valid());

  dialogActions = computed<DialogAction<boolean>[]>(() => [
    {
      type: "confirm",
      label: $localize`:@@common.rollover:Rollover`,
      value: true,
      disabled: this.enrollmentPolicyState().state === "pending" || this.descriptionInvalid()
    }
  ]);

  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

  // Only required if we later add the reopen rollover dialog function
  enrollResponse: WritableSignal<EnrollmentResponse | null> = signal(null);

  constructor() {
    super();
    const mapperObject = getTokenApiPayloadMapper(this.data.token.tokentype);
    if (!mapperObject) {
      return;
    }
    this.token.set(mapperObject.fromTokenDetailsToEnrollmentData(this.data.token));
    this.tokenService.selectedTokenType.set({ key: this.token()!.type, name: "", text: "", info: "" });
    this.serial.set(this.token()!.serial);
  }

  private _toPromise<T>(observable: Observable<T> | Promise<T>): Promise<T> {
    if (observable instanceof Promise) {
      return observable;
    } else {
      return lastValueFrom(observable);
    }
  }

  async rolloverToken() {
    if (!this.token()) {
      this.notificationService.warning($localize`:@@token.noTokenSelected:No token selected for rollover.`);
      return;
    }

    if (this.descriptionInvalid()) {
      this.descriptionForm().markAsTouched();
      return;
    }

    const strategy = this.enrollSwitch()?.currentStrategy();
    if (!strategy) {
      this.notificationService.warning(
        $localize`:@@token.rolloverAction:Rollover action is not available for the selected token type.`
      );
      return;
    }

    const basicOptions: TokenEnrollmentData = {
      type: this.token()!.type,
      serial: this.token()!.serial,
      description: this.needsDescriptionInput() ? this.description() : this.token()!.description,
      rollover: true
    };

    const enrollmentArgs = strategy.buildEnrollmentArgs(basicOptions);
    if (!enrollmentArgs) {
      this.notificationService.warning(
        $localize`:@@token.pleaseFillAll:Please fill in all required fields or correct invalid entries.`
      );
      return;
    }

    let enrollmentResponse: EnrollmentResponse | null;
    try {
      enrollmentResponse = await this._toPromise(this.tokenService.enrollToken(enrollmentArgs));
    } catch {
      // enrollToken() has already notified about the failure.
      return;
    }

    this.enrolledDialogData.set({
      response: enrollmentResponse,
      enrollParameters: enrollmentArgs,
      tokenType: enrollmentArgs.data.type,
      rollover: true,
      onEnrollmentResponseChange: (response) => this.updateEnrollmentResponse(response)
    });

    // Complete rollover
    // Push, passkey, webauthn (TODO: maybe we can integrate this into the complete enrollment dialog component)
    if (strategy.onEnrollmentResponse && enrollmentResponse) {
      const stepResult = await strategy.onEnrollmentResponse(enrollmentResponse, enrollmentArgs.data);
      enrollmentResponse = stepResult === ENROLLMENT_CANCELLED ? null : stepResult;
    }

    // two step enrollment + handles further enrollment steps (verify + success dialog)
    this.dialogRef.close();
    this.handleCompleteEnrollment(enrollmentResponse);
  }

  updateEnrollmentResponse(response: EnrollmentResponse): void {
    this.enrollResponse.set(response);
    this.enrolledDialogData.update((data) => (data ? { ...data, response: response } : data));
  }

  handleCompleteEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (enrollmentResponse?.detail.rollout_state !== "clientwait") {
      return this.handleVerifyEnrollment(enrollmentResponse);
    }

    const dialogRef = this.dialogService.openDialog({
      component: TokenCompleteEnrollmentComponent,
      data: this.enrolledDialogData(),
      configOverride: { autoFocus: "input", disableClose: true }
    });
    dialogRef.afterClosed().subscribe((result) => {
      this.tokenService.tokenDetailResource.reload();
      if (result && result !== ENROLLMENT_CANCELLED) {
        this.enrollResponse.set(result);
        this.enrolledDialogData.set({
          ...this.enrolledDialogData()!,
          showEnrollData: false
        });
        this.handleVerifyEnrollment(result);
      }
    });
  }

  handleVerifyEnrollment(enrollmentResponse: EnrollmentResponse | null): void {
    if (!this.enrolledDialogData() || !enrollmentResponse) return;

    this.enrollResponse.set(enrollmentResponse);
    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: enrollmentResponse
    });

    if (!enrollmentResponse?.detail?.verify) {
      // No verify required, directly open last step dialog
      return this._handleEnrollmentResponse(enrollmentResponse);
    }

    // Open verify dialog
    const dialogRef = this.dialogService.openDialog({
      component: TokenVerifyEnrollmentComponent,
      data: this.enrolledDialogData(),
      configOverride: { autoFocus: "input", disableClose: true }
    });
    dialogRef.afterClosed().subscribe((result) => {
      this.tokenService.tokenDetailResource.reload();
      if (result && result !== ENROLLMENT_CANCELLED) {
        this.enrollResponse.set(result);
        this._handleEnrollmentResponse(result);
      }
    });
  }

  protected openLastStepDialog(response: EnrollmentResponse | null): void {
    if (!response) {
      this.notificationService.warning($localize`:@@token.noRolloverResponse:No rollover response available.`);
      return;
    }

    this.enrolledDialogData.set({
      ...this.enrolledDialogData()!,
      response: response
    });

    const dialogRef = this.dialogService.openDialog({
      component: TokenEnrollmentLastStepDialogComponent,
      data: this.enrolledDialogData(),
      configOverride: {
        disableClose: NO_DISMISS_LAST_STEP_TOKEN_TYPES.includes(this.enrolledDialogData()?.tokenType ?? "")
      }
    });

    dialogRef.afterClosed().subscribe(() => {
      this.tokenService.tokenDetailResource.reload();
    });
  }

  protected _handleEnrollmentResponse(response: EnrollmentResponse): void {
    const detail = response.detail || {};
    const rolloutState = detail.rollout_state;

    if (rolloutState === "clientwait") {
      return;
    }

    this.openLastStepDialog(response);
  }
}
