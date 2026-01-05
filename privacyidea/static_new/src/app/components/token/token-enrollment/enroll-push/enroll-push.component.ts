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
import { Component, EventEmitter, inject, Input, OnInit, Output, signal } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { Tokens, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import {
  PushApiPayloadMapper,
  PushEnrollmentData
} from "../../../../mappers/token-api-payload/push-token-api-payload.mapper";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ReopenDialogFn } from "../token-enrollment.component";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { PiResponse } from "../../../../app.component";
import { lastValueFrom } from "rxjs";
import { MatDialogRef } from "@angular/material/dialog";
import { TokenEnrollmentFirstStepDialogComponent } from "../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component";

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

  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: PushEnrollmentData;
      mapper: TokenApiPayloadMapper<PushEnrollmentData>;
    } | null
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();
  @Output() onEnrollmentResponseChange = new EventEmitter<
    (enrollmentResponse: EnrollmentResponse) => Promise<EnrollmentResponse | null>
  >();

  pushForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this.onEnrollmentResponseChange.emit(this.onEnrollmentResponse.bind(this));
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: PushEnrollmentData;
    mapper: TokenApiPayloadMapper<PushEnrollmentData>;
  } | null => {
    const enrollmentData: PushEnrollmentData = {
      ...basicOptions,
      type: "push"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  async onEnrollmentResponse(initResponse: EnrollmentResponse): Promise<EnrollmentResponse | null> {
    if (!initResponse) {
      return null;
    }
    const pollResponse = await this.pollTokenRolloutState(initResponse, 5000).catch(() => {
      return null;
    });
    if (!pollResponse) {
      return null;
    } else {
      return {
        ...initResponse,
        detail: { ...initResponse.detail, rollout_state: pollResponse.result?.value?.tokens[0].rollout_state }
      };
    }
  }
  firstStepDialogRef: MatDialogRef<
    {
      enrollmentResponse: EnrollmentResponse<EnrollmentResponseDetail>;
    },
    boolean
  > | null = null;

  private pollTokenRolloutState = (
    initResponse: EnrollmentResponse,
    initDelay: number
  ): Promise<PiResponse<Tokens>> => {
    this.firstStepDialogRef = this._openStepOneDialog(initResponse);
    this.firstStepDialogRef.afterClosed().subscribe(() => {
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
          this.firstStepDialogRef?.close(true);
        }
      }
    });
    return lastValueFrom(observable);
  };

  private _openStepOneDialog(enrollmentResponse: EnrollmentResponse): MatDialogRef<
    {
      enrollmentResponse: EnrollmentResponse<EnrollmentResponseDetail>;
    },
    boolean
  > {
    this.reopenDialogChange.emit(async () => {
      if (this.firstStepDialogRef && this.dialogService.isDialogOpen(this.firstStepDialogRef)) {
        return null;
      }

      const pollResponse = await this.pollTokenRolloutState(enrollmentResponse, 0);
      return {
        ...enrollmentResponse,
        detail: { ...enrollmentResponse.detail, rollout_state: pollResponse.result?.value?.tokens[0].rollout_state }
      };
    });

    return this.dialogService.openDialog({
      component: TokenEnrollmentFirstStepDialogComponent,
      data: { enrollmentResponse }
    });
  }
}
