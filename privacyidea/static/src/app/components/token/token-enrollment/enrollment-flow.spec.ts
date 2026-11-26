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
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { DialogService } from "@services/dialog/dialog.service";
import { EnrollTokenArguments } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { Subject, throwError } from "rxjs";

const response = (detail: Record<string, unknown>) =>
  ({ result: { status: true }, detail: { serial: "OATH0001", ...detail } }) as unknown as EnrollmentResponse;

describe("EnrollmentFlow", () => {
  let dialogService: MockDialogService;
  let options: EnrollmentFlowOptions & {
    onStepClosed: jest.Mock;
    onCancelled: jest.Mock;
    onIncomplete: jest.Mock;
    onCompleted: jest.Mock;
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: DialogService, useClass: MockDialogService }]
    });
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
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
    // The success step alone never changes the step, so the dialog fits its content.
    expect(flow.fixedSize()).toBe(false);
  });

  it("runs two-step completion, verification and success in one dialog", () => {
    const first = response({ rollout_state: "clientwait" });
    const completed = response({ rollout_state: "verify", verify: { message: "Enter OTP" } });
    const verified = response({ rollout_state: "enrolled" });
    const flow = startFlow(first);

    flow.continue(first);
    expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
    expect(flow.fixedSize()).toBe(true);

    flow.finishStep(completed);
    expect(flow.stepComponent()).toBe(TokenVerifyEnrollmentComponent);
    expect(flow.dialogData()?.response).toBe(completed);
    // The data shown for the second step is outdated once the token is complete.
    expect(flow.dialogData()?.showEnrollData).toBe(false);

    flow.finishStep(verified);
    expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    expect(flow.dialogData()?.response).toBe(verified);
    // The size chosen when the dialog opened stays, so it does not change at the last step.
    expect(flow.fixedSize()).toBe(true);
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

  it("cannot reopen a closed FIDO2 registration, the token is kept", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first, { kind: "fido2", register: jest.fn() });
    flow.continue(first);
    expect(flow.resumable()).toBe(false);

    flow.close();

    expect(options.onIncomplete).toHaveBeenCalledTimes(1);
    expect(options.onCancelled).not.toHaveBeenCalled();
    expect(flow.dialogData()).toBeNull();
    flow.resume();
    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
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

  describe("while the token is being deleted", () => {
    const pushFlow = (): EnrollmentFlow => {
      const first = response({ rollout_state: "clientwait" });
      const flow = startFlow(first, { kind: "push" });
      flow.continue(first);
      return flow;
    };

    it("drops a step result once the token is gone", () => {
      const flow = pushFlow();
      const deletion = new Subject<void>();
      flow.deleteToken(deletion).subscribe();

      flow.finishStep(response({ rollout_state: "enrolled" }));
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
      deletion.next();
      deletion.complete();
      // A poll that was already running when the deletion finished.
      flow.finishStep(response({ rollout_state: "enrolled" }));
      flow.finishStep(ENROLLMENT_CANCELLED);

      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
      expect(options.onCompleted).not.toHaveBeenCalled();
      expect(options.onCancelled).toHaveBeenCalledTimes(1);
    });

    it("shows the success step if the deletion fails after the token was registered", () => {
      const flow = pushFlow();
      const deletion = new Subject<void>();
      flow.deleteToken(deletion).subscribe({ error: () => undefined });

      flow.finishStep(response({ rollout_state: "enrolled" }));
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
      deletion.error(new Error("denied"));

      expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
      expect(options.onCompleted).toHaveBeenCalledTimes(1);
      expect(options.onCancelled).not.toHaveBeenCalled();
    });

    it("stays at the step if the deletion fails without a result and continues with the next one", () => {
      const flow = pushFlow();
      flow.deleteToken(throwError(() => new Error("denied"))).subscribe({ error: () => undefined });

      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentPushComponent);
      expect(dialogRef().close).not.toHaveBeenCalled();

      flow.finishStep(response({ rollout_state: "enrolled" }));
      expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    });
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

  describe("with the request that finishes a step", () => {
    const first = response({ rollout_state: "clientwait" });
    let finishes: boolean;
    const toResponse = (result: EnrollmentResponse) => (finishes ? result : null);
    let flow: EnrollmentFlow;
    let request: Subject<EnrollmentResponse>;

    beforeEach(() => {
      finishes = true;
      flow = startFlow(first);
      flow.continue(first);
      request = new Subject<EnrollmentResponse>();
      flow.sendStepRequest(request, toResponse, "CLIENTPART");
    });

    const answer = (result: EnrollmentResponse) => {
      request.next(result);
      request.complete();
    };

    it("keeps the sent input while the request runs and moves on with its response", () => {
      expect(flow.sentInput()).toBe("CLIENTPART");

      answer(response({ rollout_state: "enrolled" }));

      expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
      expect(flow.sentInput()).toBeNull();
      expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    });

    it("does not send a second request while one runs", () => {
      const second = new Subject<EnrollmentResponse>();

      flow.sendStepRequest(second, toResponse, "OTHER");

      expect(second.observed).toBe(false);
      expect(flow.sentInput()).toBe("CLIENTPART");
    });

    it("stays at the step when the response does not finish it, or the request failed", () => {
      finishes = false;
      request.next(response({ rollout_state: "clientwait" }));
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);

      request.error(new Error("failed"));
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
      expect(flow.sentInput()).toBeNull();
    });

    it("moves on without opening the dialog after it was closed, and the reopen shows the next step", () => {
      flow.close();
      answer(response({ rollout_state: "verify", verify: { message: "Enter OTP" } }));

      expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
      expect(flow.step()).toBe("verify");

      flow.resume();
      expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
      expect(flow.stepComponent()).toBe(TokenVerifyEnrollmentComponent);
    });

    it("reports a token completed after the dialog was closed", () => {
      flow.close();
      answer(response({ rollout_state: "enrolled" }));

      expect(options.onIncomplete).toHaveBeenCalledTimes(1);
      expect(options.onCompleted).toHaveBeenCalledTimes(1);
      expect(dialogService.openDialog).toHaveBeenCalledTimes(1);

      flow.resume();
      expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
    });

    it("keeps the sent input for a step reopened while the request runs", () => {
      flow.close();
      flow.resume();

      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
      expect(flow.sentInput()).toBe("CLIENTPART");
    });

    it("ignores the response once the enrollment was reset or another one started", () => {
      flow.reset();
      expect(flow.sentInput()).toBeNull();
      const next = response({ serial: "OATH0002", rollout_state: "clientwait" });
      flow.start({ response: next, enrollParameters: {} as EnrollTokenArguments, tokenType: "hotp" });
      flow.continue(next);
      flow.sendStepRequest(new Subject<EnrollmentResponse>(), toResponse, "NEXT");

      answer(response({ rollout_state: "enrolled" }));

      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentTwoStepComponent);
      expect(flow.dialogData()?.response).toBe(next);
      expect(flow.sentInput()).toBe("NEXT");
    });
  });

  describe("with the final request of a FIDO2 registration", () => {
    const first = response({ rollout_state: "clientwait" });
    let flow: EnrollmentFlow;
    let request: Subject<EnrollmentStepResult>;

    beforeEach(() => {
      flow = startFlow(first, { kind: "fido2", register: jest.fn() });
      flow.continue(first);
      request = new Subject<EnrollmentStepResult>();
      flow.sendStepRequest(request, (result) => result);
    });

    const answer = (result: EnrollmentStepResult) => {
      request.next(result);
      request.complete();
    };

    it("keeps the enrollment when the dialog closes while the request runs, and the reopen waits for it", () => {
      expect(flow.resumable()).toBe(true);

      flow.close();
      expect(options.onIncomplete).toHaveBeenCalledTimes(1);
      expect(flow.dialogData()).not.toBeNull();

      flow.resume();
      expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentFido2Component);
    });

    it("moves on to the success step without opening the dialog once the request ends after the close", () => {
      flow.close();
      answer(response({ rollout_state: "enrolled" }));

      expect(flow.step()).toBe("success");
      expect(options.onCompleted).toHaveBeenCalledTimes(1);
      expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    });

    it("ends the enrollment once the request failed after the close", () => {
      flow.close();
      answer(null);

      expect(flow.dialogData()).toBeNull();
      expect(flow.step()).toBeNull();
    });

    it("reports a token deleted after the close", () => {
      flow.close();
      answer(ENROLLMENT_CANCELLED);

      expect(options.onCancelled).toHaveBeenCalledTimes(1);
      expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    });

    it("reports a failed request in the open dialog, which then cannot be resumed", () => {
      answer(null);

      expect(flow.stepRequestFailed()).toBe(true);
      expect(flow.stepComponent()).toBe(TokenCompleteEnrollmentFido2Component);
      expect(flow.resumable()).toBe(false);

      flow.sendStepRequest(new Subject<EnrollmentStepResult>(), (result) => result);
      expect(flow.stepRequestFailed()).toBe(false);
    });
  });

  it("tells when the dialog is closed, at any step", async () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first);
    await expect(flow.whenClosed()).resolves.toBeUndefined();

    flow.continue(first);
    let closed = false;
    void flow.whenClosed().then(() => (closed = true));
    flow.finishStep(response({ rollout_state: "enrolled" }));
    await new Promise((resolve) => setTimeout(resolve));
    expect(closed).toBe(false);

    flow.close();
    await new Promise((resolve) => setTimeout(resolve));
    expect(closed).toBe(true);
  });

  describe("container", () => {
    it("keeps the container of the first response when later responses do not repeat it", () => {
      const first = response({ rollout_state: "clientwait", container_serial: "CONT0001" });
      const flow = startFlow(first, { kind: "fido2", register: jest.fn() });
      flow.continue(first);

      flow.finishStep(response({ rollout_state: "verify", verify: { message: "Enter OTP" } }));
      expect(flow.containerSerial()).toBe("CONT0001");

      flow.finishStep(response({ rollout_state: "enrolled" }));
      expect(flow.stepComponent()).toBe(TokenEnrollmentSuccessComponent);
      expect(flow.containerSerial()).toBe("CONT0001");
    });

    it("shows no container the server did not add the token to", () => {
      const first = response({ rollout_state: "enrolled" });
      const flow = TestBed.runInInjectionContext(() => new EnrollmentFlow(options));
      flow.start({
        response: first,
        enrollParameters: { data: { containerSerial: "CONT0001" } } as unknown as EnrollTokenArguments,
        tokenType: "hotp"
      });

      expect(flow.containerSerial()).toBe("");
    });

    it("forgets the container of an earlier enrollment", () => {
      const flow = startFlow(response({ rollout_state: "enrolled", container_serial: "CONT0001" }));

      flow.reset();
      expect(flow.containerSerial()).toBe("");

      flow.start({
        response: response({ rollout_state: "enrolled" }),
        enrollParameters: {} as EnrollTokenArguments,
        tokenType: "hotp"
      });
      expect(flow.containerSerial()).toBe("");
    });
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
