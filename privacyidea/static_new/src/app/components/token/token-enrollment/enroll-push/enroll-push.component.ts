import { Component, EventEmitter, OnInit, Output, signal } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { Tokens, TokenService } from '../../../../services/token/token.service';

import { MatDialogRef } from '@angular/material/dialog';
import { lastValueFrom } from 'rxjs';
import { PiResponse } from '../../../../app.component';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { PushApiPayloadMapper } from '../../../../mappers/token-api-payload/push-token-api-payload.mapper';
import { DialogService } from '../../../../services/dialog/dialog.service';
import { TokenEnrollmentFirstStepDialogComponent } from '../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';
import { ReopenDialogFn } from '../token-enrollment.component';

export interface PushEnrollmentOptions extends TokenEnrollmentData {
  type: 'push';
  // No type-specific fields for initialization via EnrollmentOptions // Keep original comment
}

@Component({
  selector: 'app-enroll-push',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-push.component.html',
  styleUrl: './enroll-push.component.scss',
})
export class EnrollPushComponent implements OnInit {
  pollResponse = signal<PiResponse<Tokens> | undefined>(undefined);

  text = this.tokenService // Keep original initialization
    .tokenTypeOptions()
    .find((type) => type.key === 'push')?.text; // Corrected from 'spass' to 'push'

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Promise<EnrollmentResponse | null>
  >();
  @Output() reopenDialogChange = new EventEmitter<ReopenDialogFn>();
  // No specific FormControls needed for Push Token that the user sets directly.
  // generateOnServer is implicit or can be treated as a constant.
  pushForm = new FormGroup({});

  constructor(
    private tokenService: TokenService,
    private enrollmentMapper: PushApiPayloadMapper,
    private dialogService: DialogService,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = async (
    basicOptions: TokenEnrollmentData,
  ): Promise<EnrollmentResponse | null> => {
    const enrollmentData: PushEnrollmentOptions = {
      ...basicOptions,
      type: 'push',
    };
    const initResponse = await lastValueFrom(
      this.tokenService.enrollToken({
        data: enrollmentData,
        mapper: this.enrollmentMapper,
      }),
    ).catch((error) => {
      return null;
    });
    if (!initResponse) {
      return null;
    }
    const pollResponse = await this.pollTokenRolloutState(
      initResponse,
      5000,
    ).catch((error) => {
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
    initDelay: number,
  ): Promise<PiResponse<Tokens>> => {
    this._openStepOneDialog(initResponse)
      .afterClosed()
      .subscribe(() => {
        this.tokenService.stopPolling();
        this.pollResponse.set(undefined);
      });
    const observable = this.tokenService.pollTokenRolloutState({
      tokenSerial: initResponse.detail.serial,
      initDelay,
    });
    observable.subscribe({
      next: (pollResponse) => {
        this.pollResponse.set(pollResponse);
        if (
          pollResponse.result?.value?.tokens[0].rollout_state !== 'clientwait'
        ) {
          this.dialogService.closeTokenEnrollmentFirstStepDialog();
        }
      },
    });
    return lastValueFrom(observable);
  };

  private _openStepOneDialog(
    enrollmentResponse: EnrollmentResponse,
  ): MatDialogRef<TokenEnrollmentFirstStepDialogComponent, any> {
    this.reopenDialogChange.emit(async () => {
      if (!this.dialogService.isTokenEnrollmentFirstStepDialogOpen) {
        await this.pollTokenRolloutState(enrollmentResponse, 0);
        return enrollmentResponse;
      }
      return null;
    });

    return this.dialogService.openTokenEnrollmentFirstStepDialog({
      data: { enrollmentResponse },
    });
  }
  private _closeStepOneDialog(): void {
    this.reopenDialogChange.emit(undefined);
    this.dialogService.closeTokenEnrollmentFirstStepDialog();
  }
}
