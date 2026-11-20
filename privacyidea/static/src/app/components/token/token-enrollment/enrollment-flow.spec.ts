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
import { TestBed } from "@angular/core/testing";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  EnrollmentFirstStep,
  EnrollmentFlow,
  EnrollmentFlowOptions
} from "@components/token/token-enrollment/enrollment-flow";
import { TokenCompleteEnrollmentFido2Component } from "@components/token/token-enrollment/token-complete-enrollment-fido2/token-complete-enrollment-fido2.component";
import { TokenCompleteEnrollmentPushComponent } from "@components/token/token-enrollment/token-complete-enrollment-push/token-complete-enrollment-push.component";
import { TokenCompleteEnrollmentTwoStepComponent } from "@components/token/token-enrollment/token-complete-enrollment-two-step/token-complete-enrollment-two-step.component";
import { TokenEnrollmentDialogComponent } from "@components/token/token-enrollment/token-enrollment-dialog/token-enrollment-dialog.component";
import { TokenEnrollmentSuccessComponent } from "@components/token/token-enrollment/token-enrollment-success/token-enrollment-success.component";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { EnrollTokenArguments } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockNotificationService } from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";

const response = (detail: Record<string, unknown>) =>
  ({ result: { status: true }, detail: { serial: "OATH0001", ...detail } }) as unknown as EnrollmentResponse;

describe("EnrollmentFlow", () => {
  let dialogService: MockDialogService;
  let notificationService: MockNotificationService;
  let options: EnrollmentFlowOptions & {
    onStepClosed: jest.Mock;
    onCancelled: jest.Mock;
    onIncomplete: jest.Mock;
    onCompleted: jest.Mock;
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    options = {
      successStep: () => TokenEnrollmentSuccessComponent,
      onStepClosed: jest.fn(),
      onCancelled: jest.fn(),
      onIncomplete: jest.fn(),
      onCompleted: jest.fn()
    };
  });

  const startFlow = (first: EnrollmentResponse, firstStep: EnrollmentFirstStep | null = null): EnrollmentFlow => {
    const flow = TestBed.runInInjectionContext(() => new EnrollmentFlow(options));
    flow.start({ response: first, enrollParameters: {} as EnrollTokenArguments, tokenType: "hotp" }, firstStep);
    return flow;
  };
  const dialogRef = (call = 0) => dialogService.openDialog.mock.results[call].value as MockMatDialogRef<unknown>;

  it("shows the success step directly when no further step is needed", () => {
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);

    flow.continue(enrolled);

    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    expect(dialogService.openDialog).toHaveBeenCalledWith({
      component: TokenEnrollmentDialogComponent,
      data: { flow },
      configOverride: { disableClose: true, autoFocus: false }
    });
    expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(flow.dialogData()?.response).toBe(enrolled);
    expect(options.onCompleted).toHaveBeenCalledTimes(1);
  });

  it("runs two-step completion, verification and success in one dialog", () => {
    const first = response({ rollout_state: "clientwait" });
    const completed = response({ rollout_state: "verify", verify: { message: "Enter OTP" } });
    const verified = response({ rollout_state: "enrolled" });
    const flow = startFlow(first);

    flow.continue(first);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);

    flow.finishStep(completed);
    expect(flow.stepComponent()).toBe(TokenVerifyEnrollmentComponent);
    expect(flow.dialogData()?.response).toBe(completed);
    // The data shown for the second step is outdated once the token is complete.
    expect(flow.dialogData()?.showEnrollData).toBe(false);

    flow.finishStep(verified);
    expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(flow.dialogData()?.response).toBe(verified);
    expect(options.onCompleted).toHaveBeenCalledTimes(1);
    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    expect(options.onStepClosed).toHaveBeenCalledTimes(2);

    dialogRef().close();
    expect(options.onStepClosed).toHaveBeenCalledTimes(3);
    expect(options.onIncomplete).not.toHaveBeenCalled();
  });

  it("shows the first step of the token type before the response decides the next step", () => {
    const first = response({ rollout_state: "clientwait" });
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(first, { kind: "push" });

    flow.continue(first);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
    expect(flow.firstStep).toEqual({ kind: "push" });

    flow.finishStep(enrolled);
    expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(flow.firstStep).toBeNull();
    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    expect(options.onCompleted).toHaveBeenCalledTimes(1);
  });

  it("continues a FIDO2 registration with the verification the response asks for", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first, { kind: "fido2", register: jest.fn() });

    flow.continue(first);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentFido2Component);

    flow.finishStep(response({ verify: { message: "Enter OTP" } }));
    expect(flow.stepComponent()).toBe(TokenVerifyEnrollmentComponent);
  });

  it("reopens a closed first step and tells it that it was reopened", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first, { kind: "push" });
    flow.continue(first);
    expect(flow.reopened).toBe(false);
    flow.close();
    expect(options.onIncomplete).toHaveBeenCalledTimes(1);

    flow.resume();

    expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
    expect(flow.reopened).toBe(true);
  });

  it("forgets the first step of an earlier enrollment", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first, { kind: "push" });
    flow.continue(first);
    flow.close();
    flow.resume();
    flow.close();

    flow.start({ response: first, enrollParameters: {} as EnrollTokenArguments, tokenType: "hotp" });
    flow.continue(first);

    expect(flow.reopened).toBe(false);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
  });

  it("emits stepFinished when the step changes and when the dialog closes", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first);
    const finished = jest.fn();
    flow.continue(first);
    flow.stepFinished.subscribe(finished);

    flow.finishStep(response({ rollout_state: "enrolled" }));
    expect(finished).toHaveBeenCalledTimes(1);

    flow.close();
    expect(finished).toHaveBeenCalledTimes(2);
  });

  it("closes the dialog and reports a deleted token", () => {
    const first = response({ verify: { message: "Enter OTP" } });
    const flow = startFlow(first);

    flow.continue(first);
    flow.finishStep(ENROLLMENT_CANCELLED);

    expect(dialogRef().close).toHaveBeenCalled();
    expect(options.onCancelled).toHaveBeenCalledTimes(1);
    expect(options.onIncomplete).not.toHaveBeenCalled();
  });

  it("reports a dialog closed before the enrollment finished and resumes at the same step", () => {
    const first = response({ verify: { message: "Enter OTP" } });
    const flow = startFlow(first);

    flow.continue(first);
    flow.close();

    expect(options.onIncomplete).toHaveBeenCalledTimes(1);
    expect(options.onCompleted).not.toHaveBeenCalled();

    flow.resume();
    expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
    expect(flow.stepComponent()).toBe(TokenVerifyEnrollmentComponent);
  });

  it("does not finish the enrollment again when the success step is resumed", () => {
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);
    flow.continue(enrolled);
    flow.close();

    flow.resume();

    expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(options.onCompleted).toHaveBeenCalledTimes(1);
    expect(options.onIncomplete).not.toHaveBeenCalled();
  });

  it("keeps the success step closed while a reason blocks it", () => {
    options.successBlockedReason = () => "User missing";
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);

    flow.continue(enrolled);

    expect(notificationService.warning).toHaveBeenCalledWith("User missing");
    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(options.onCompleted).not.toHaveBeenCalled();
  });

  it("reads the success step when it opens", () => {
    class OtherSuccessStep extends TokenEnrollmentSuccessComponent {}
    let successStep: typeof TokenEnrollmentSuccessComponent = TokenEnrollmentSuccessComponent;
    options.successStep = () => successStep;
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);
    successStep = OtherSuccessStep;

    flow.continue(enrolled);

    expect(flow.stepComponent()).toBe(OtherSuccessStep);
  });

  it("does nothing before an enrollment started or after it was reset", () => {
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);
    flow.reset();

    flow.continue(enrolled);
    flow.resume();

    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(flow.step()).toBeNull();
  });

  it("keeps a regenerated response for the next step", () => {
    const first = response({ rollout_state: "clientwait", googleurl: { img: "initial" } });
    const regenerated = response({ rollout_state: "clientwait", googleurl: { img: "regenerated" } });
    const flow = startFlow(first);

    flow.dialogData()?.onEnrollmentResponseChange?.(regenerated);
    flow.resume();

    expect(flow.dialogData()?.response).toBe(regenerated);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
  });
});
