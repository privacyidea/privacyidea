import { Component, EventEmitter, OnInit, Output, signal } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {
  EnrollmentResponse,
  Tokens,
  TokenService,
} from '../../../../services/token/token.service';

import { from, lastValueFrom, Observable } from 'rxjs';
import { TokenEnrollmentData } from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { PushApiPayloadMapper } from '../../../../mappers/token-api-payload/push-token-api-payload.mapper';
import { DialogService } from '../../../../services/dialog/dialog.service';
import { PiResponse } from '../../../../app.component';

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
    (
      basicOptions: TokenEnrollmentData,
    ) => Promise<EnrollmentResponse> | undefined
  >();

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
  ): Promise<EnrollmentResponse> => {
    const enrollmentData: PushEnrollmentOptions = {
      ...basicOptions,
      type: 'push',
      // Removed generateOnServer as per "DO NOT CHANGE OTHER LINES"
    };
    const initResponse = await lastValueFrom(
      this.tokenService.enrollToken({
        data: enrollmentData,
        mapper: this.enrollmentMapper,
      }),
    );
    await this.pollTokenRolloutStat(initResponse, 5000);
    return initResponse;
  };

  private pollTokenRolloutStat(
    initResponse: EnrollmentResponse,
    initDelay: number,
  ) {
    this.dialogService
      .openTokenEnrollmentFirstStepDialog({
        data: {
          response: initResponse,
        },
      })
      .afterClosed()
      .subscribe(() => {
        this.tokenService.stopPolling();
        this.pollResponse.set(undefined);
      });
    const tokenSerial = initResponse.detail.serial;
    const observable = this.tokenService.pollTokenRolloutState(
      tokenSerial,
      initDelay,
    );
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
  }
}
