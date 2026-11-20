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
import { EnrollmentResponse, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { getTokenApiPayloadMapper } from "@app/mappers/token-api-payload/token-api-payload-mapper-registry";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { EnrollmentFlow } from "@components/token/token-enrollment/enrollment-flow";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { DialogAction } from "@models/dialog";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { Observable, lastValueFrom } from "rxjs";

@Component({
  selector: "app-token-rollover",
  imports: [DialogWrapperComponent, EnrollTokenTypeSwitchComponent],
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
  // The rollover dialog closes after the first step, the flow runs the remaining steps on its own.
  readonly enrollmentFlow = new EnrollmentFlow({
    successStep: () => TokenEnrollmentLastStepDialogComponent,
    onStepClosed: () => this.tokenService.tokenDetailResource.reload()
  });

  dialogActions = signal<DialogAction<boolean>[]>([
    {
      type: "confirm",
      label: $localize`:@@common.rollover:Rollover`,
      value: true,
      disabled: false
    }
  ]);

  protected readonly enrollSwitch = viewChild(EnrollTokenTypeSwitchComponent);

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
      description: this.token()!.description,
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

    this.enrollmentFlow.start(
      {
        response: enrollmentResponse,
        enrollParameters: enrollmentArgs,
        tokenType: enrollmentArgs.data.type,
        rollover: true
      },
      enrollmentResponse ? (strategy.firstStep?.(enrollmentResponse, enrollmentArgs.data) ?? null) : null
    );
    // The enrollment dialog takes over, so it does not open on top of the rollover form.
    this.dialogRef.close();
    if (enrollmentResponse) {
      this.enrollmentFlow.continue(enrollmentResponse);
    }
  }
}
