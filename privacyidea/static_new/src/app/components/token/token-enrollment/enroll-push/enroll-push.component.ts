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
import { Component, EventEmitter, inject, OnInit, Output, signal } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { Tokens, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { MatDialogRef } from "@angular/material/dialog";
import { lastValueFrom } from "rxjs";
import { PiResponse } from "../../../../app.component";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { PushApiPayloadMapper } from "../../../../mappers/token-api-payload/push-token-api-payload.mapper";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { TokenEnrollmentFirstStepDialogComponent } from "../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";
import { ReopenDialogFn } from "../token-enrollment.component";

export interface PushEnrollmentOptions extends TokenEnrollmentData {
  type: "push";
}

@Component({
  selector: "app-enroll-push",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-push.component.html",
  styleUrl: "./enroll-push.component.scss"
})
export class EnrollPushComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly enrollmentMapper: PushApiPayloadMapper = inject(PushApiPayloadMapper);

  pollResponse = signal<PiResponse<Tokens> | undefined>(undefined);

  text = this.tokenService.tokenTypeOptions().find((type) => type.key === "push")?.text;

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();

  pushForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = async (basicOptions: TokenEnrollmentData): Promise<EnrollmentResponse | null> => {
    const enrollmentData: PushEnrollmentOptions = {
      ...basicOptions,
      type: "push"
    };
    const initResponse = await lastValueFrom(
      this.tokenService.enrollToken({
        data: enrollmentData,
        mapper: this.enrollmentMapper
      })
    ).catch(() => {
      return null;
    });
    if (!initResponse) {
      return null;
    }
    const pollResponse = await this.pollTokenRolloutState(initResponse, 5000).catch(() => {
      return null;
    });
    if (!pollResponse) {
      return null;
    } else {
      return initResponse;
    }
  };

  private pollTokenRolloutState = (
    initResponse: EnrollmentResponse,
    initDelay: number
  ): Promise<PiResponse<Tokens>> => {
    this._openStepOneDialog(initResponse)
      .afterClosed()
      .subscribe(() => {
        this.tokenService.stopPolling();
        this.pollResponse.set(undefined);
      });
    const observable = this.tokenService.pollTokenRolloutState({
      tokenSerial: initResponse.detail.serial,
      initDelay
    });
    observable.subscribe({
      next: (pollResponse) => {
        this.pollResponse.set(pollResponse);
        if (pollResponse.result?.value?.tokens[0].rollout_state !== "clientwait") {
          this.dialogService.closeTokenEnrollmentFirstStepDialog();
        }
      }
    });
    return lastValueFrom(observable);
  };

  private _openStepOneDialog(
    enrollmentResponse: EnrollmentResponse
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    this.reopenDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen) {
        await this.pollTokenRolloutState(enrollmentResponse, 0);
        return enrollmentResponse;
      }
      return null;
    });

    return this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse }
    });
  }

  private _closeStepOneDialog(): void {
    this.reopenDialogChange.emit(undefined);
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
