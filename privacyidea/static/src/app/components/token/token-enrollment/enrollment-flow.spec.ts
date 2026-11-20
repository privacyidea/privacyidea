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
import { EnrollmentFlow, EnrollmentFlowOptions } from "@components/token/token-enrollment/enrollment-flow";
import { TokenCompleteEnrollmentComponent } from "@components/token/token-enrollment/token-complete-enrollment/token-complete-enrollment.component";
import { TokenEnrollmentLastStepDialogComponent } from "@components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
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
      successDialog: () => TokenEnrollmentLastStepDialogComponent,
      onStepClosed: jest.fn(),
      onCancelled: jest.fn(),
      onIncomplete: jest.fn(),
      onCompleted: jest.fn()
    };
  });

  const startFlow = (first: EnrollmentResponse): EnrollmentFlow => {
    const flow = TestBed.runInInjectionContext(() => new EnrollmentFlow(options));
    flow.start({ response: first, enrollParameters: {} as EnrollTokenArguments, tokenType: "hotp" });
    return flow;
  };
  const openedComponent = (call: number) => dialogService.openDialog.mock.calls[call][0].component;
  const dialogRef = (call: number) => dialogService.openDialog.mock.results[call].value as MockMatDialogRef<unknown>;

  it("opens the success dialog directly when no further step is needed", () => {
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);

    flow.continue(enrolled);

    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        component: TokenEnrollmentLastStepDialogComponent,
        data: expect.objectContaining({ response: enrolled })
      })
    );
    expect(options.onCompleted).toHaveBeenCalledTimes(1);
  });

  it("runs two-step completion, verification and success in this order", () => {
    const first = response({ rollout_state: "clientwait" });
    const completed = response({ rollout_state: "verify", verify: { message: "Enter OTP" } });
    const verified = response({ rollout_state: "enrolled" });
    const flow = startFlow(first);

    flow.continue(first);
    expect(openedComponent(0)).toBe(TokenCompleteEnrollmentComponent);
    expect(dialogService.openDialog.mock.calls[0][0].configOverride).toEqual({
      autoFocus: "input",
      disableClose: true
    });

    dialogRef(0).close(completed);
    expect(openedComponent(1)).toBe(TokenVerifyEnrollmentComponent);
    expect(flow.dialogData()?.response).toBe(completed);
    // The data shown for the second step is outdated once the token is complete.
    expect(flow.dialogData()?.showEnrollData).toBe(false);

    dialogRef(1).close(verified);
    expect(openedComponent(2)).toBe(TokenEnrollmentLastStepDialogComponent);
    expect(flow.dialogData()?.response).toBe(verified);
    expect(options.onCompleted).toHaveBeenCalledTimes(1);

    dialogRef(2).close();
    expect(options.onStepClosed).toHaveBeenCalledTimes(3);
  });

  it("reports a cancelled step and opens nothing after it", () => {
    const first = response({ verify: { message: "Enter OTP" } });
    const flow = startFlow(first);

    flow.continue(first);
    dialogRef(0).close(ENROLLMENT_CANCELLED);

    expect(options.onCancelled).toHaveBeenCalledTimes(1);
    expect(options.onIncomplete).not.toHaveBeenCalled();
    expect(dialogService.openDialog).toHaveBeenCalledTimes(1);
  });

  it("reports a step closed before the enrollment finished and resumes it later", () => {
    const first = response({ rollout_state: "clientwait" });
    const flow = startFlow(first);

    flow.continue(first);
    dialogRef(0).close(null);

    expect(options.onIncomplete).toHaveBeenCalledTimes(1);
    expect(options.onCompleted).not.toHaveBeenCalled();

    flow.resume();
    expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
    expect(openedComponent(1)).toBe(TokenCompleteEnrollmentComponent);
  });

  it("keeps the success dialog closed while a reason blocks it", () => {
    options.successBlockedReason = () => "User missing";
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);

    flow.continue(enrolled);

    expect(notificationService.warning).toHaveBeenCalledWith("User missing");
    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(options.onCompleted).not.toHaveBeenCalled();
  });

  it("reads the success dialog when it opens", () => {
    class OtherSuccessDialog extends TokenEnrollmentLastStepDialogComponent {}
    let successDialog: typeof TokenEnrollmentLastStepDialogComponent = TokenEnrollmentLastStepDialogComponent;
    options.successDialog = () => successDialog;
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);
    successDialog = OtherSuccessDialog;

    flow.continue(enrolled);

    expect(openedComponent(0)).toBe(OtherSuccessDialog);
  });

  it("does nothing before an enrollment started or after it was reset", () => {
    const enrolled = response({ rollout_state: "enrolled" });
    const flow = startFlow(enrolled);
    flow.reset();

    flow.continue(enrolled);
    flow.resume();

    expect(dialogService.openDialog).not.toHaveBeenCalled();
  });

  it("keeps a regenerated response for the next step", () => {
    const first = response({ rollout_state: "clientwait", googleurl: { img: "initial" } });
    const regenerated = response({ rollout_state: "clientwait", googleurl: { img: "regenerated" } });
    const flow = startFlow(first);

    flow.dialogData()?.onEnrollmentResponseChange?.(regenerated);
    flow.resume();

    expect(flow.dialogData()?.response).toBe(regenerated);
    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ response: regenerated }) })
    );
  });
});
