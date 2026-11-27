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
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollmentFirstStep, EnrollmentFlowOptions } from "@components/token/token-enrollment/enrollment-flow";
import { TokenCompleteEnrollmentFido2Component } from "@components/token/token-enrollment/token-complete-enrollment-fido2/token-complete-enrollment-fido2.component";
import { TokenCompleteEnrollmentPushComponent } from "@components/token/token-enrollment/token-complete-enrollment-push/token-complete-enrollment-push.component";
import { TokenCompleteEnrollmentTwoStepComponent } from "@components/token/token-enrollment/token-complete-enrollment-two-step/token-complete-enrollment-two-step.component";
import { TokenEnrollmentSuccessWizardComponent } from "@components/token/token-enrollment/token-enrollment-success/token-enrollment-success.wizard.component";
import { TokenVerifyEnrollmentComponent } from "@components/token/token-enrollment/token-verify-enrollment/token-verify-enrollment.component";
import { environment } from "@env/environment";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { EnrollTokenArguments, TokenEnrollmentDialogData, TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { EnrollmentDialogHarness } from "@testing/enrollment-dialog-harness";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of, Subject } from "rxjs";

const response = (detail: Record<string, unknown>) =>
  ({ result: { status: true }, detail: { serial: "OATH0001", ...detail } }) as unknown as EnrollmentResponse;
const twoStep = () => response({ rollout_state: "clientwait", "2step_output": 1 });
const verify = () => response({ rollout_state: "verify", verify: { message: "Enter OTP" } });
const enrolled = () => response({ rollout_state: "enrolled" });

describe("TokenEnrollmentDialogComponent", () => {
  let harness: EnrollmentDialogHarness;
  let dialogService: MockDialogService;
  let tokenService: MockTokenService;
  let authService: MockAuthService;
  let options: Partial<EnrollmentFlowOptions> & { onIncomplete: jest.Mock; onCancelled: jest.Mock };

  beforeEach(async () => {
    harness = new EnrollmentDialogHarness();
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ...harness.providers,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    options = { onIncomplete: jest.fn(), onCancelled: jest.fn() };
  });

  const allowDelete = (allowed: boolean) =>
    authService.actionAllowed.mockImplementation((action: string) => allowed && action === "delete");
  const open = (
    first: EnrollmentResponse,
    data: Partial<TokenEnrollmentDialogData> = {},
    firstStep: EnrollmentFirstStep | null = null
  ) => {
    harness.open(first, data, options, firstStep);
    dialogService.openDialog.mockClear();
  };
  // The answer to the next question asked on top of the dialog.
  const answer = (result: unknown) => {
    const questionRef = new MockMatDialogRef();
    questionRef.afterClosed.mockReturnValue(of(result));
    dialogService.openDialog.mockReturnValue(questionRef);
  };
  const footerLabels = () => harness.footerButtons().map((button) => button.textContent?.trim());
  const title = () => harness.element.querySelector(".pi-dialog-header h3")?.textContent?.trim();

  describe("steps", () => {
    it("stays one dialog of a fixed size from the two-step completion to the success step", () => {
      allowDelete(false);
      open(twoStep());
      const wrapper = harness.element.querySelector(".pi-dialog");
      expect(wrapper?.classList).toContain("pi-dialog-fixed");
      expect(harness.element.classList).toContain("enrollment-dialog-fixed");
      expect(harness.step()).toBeInstanceOf(TokenCompleteEnrollmentTwoStepComponent);
      expect(title()).toBe("Complete Token Enrollment");

      harness.flow.finishStep(verify());
      harness.fixture.detectChanges();
      expect(harness.step()).toBeInstanceOf(TokenVerifyEnrollmentComponent);
      expect(title()).toBe("Verify Token Enrollment");
      expect(harness.element.textContent).toContain(
        "The token was enrolled, but it still has to be verified before it can be used."
      );

      harness.flow.finishStep(enrolled());
      harness.fixture.detectChanges();
      expect(title()).toBe("Token Successfully Enrolled");
      expect(footerLabels()).toEqual(["Close"]);
      expect(harness.element.querySelector(".pi-dialog")).toBe(wrapper);
      expect(dialogService.openDialog).not.toHaveBeenCalled();
    });

    it("fits a dialog that opens at the success step to its content, at least one row of the header cards", () => {
      open(enrolled(), {
        enrollParameters: { data: { user: "alice", realm: "realm1" } } as unknown as EnrollTokenArguments
      });
      const wrapper = harness.element.querySelector(".pi-dialog");
      expect(wrapper?.classList).not.toContain("pi-dialog-fixed");
      expect(wrapper?.classList).toContain("pi-dialog-scroll-body");
      expect(harness.element.classList).not.toContain("enrollment-dialog-fixed");
      expect(harness.element.querySelectorAll(".enrolled__card")).toHaveLength(3);
      expect(harness.element.style.getPropertyValue("--enrolled-card-count")).toBe("3");
    });

    it("stays one dialog from the push QR code to the success step", () => {
      allowDelete(false);
      const poll = new Subject();
      tokenService.pollTokenRolloutState.mockReturnValue(poll);
      open(
        response({ rollout_state: "clientwait", pushurl: { img: "data:image/png;base64,QR", value: "x" } }),
        {},
        {
          kind: "push"
        }
      );
      const wrapper = harness.element.querySelector(".pi-dialog");
      expect(harness.step()).toBeInstanceOf(TokenCompleteEnrollmentPushComponent);
      expect(title()).toBe("Take Action on Your Authenticator");
      expect(footerLabels()).toEqual(["Close"]);

      poll.next({ result: { status: true, value: { tokens: [{ rollout_state: "enrolled" }] } } });
      harness.fixture.detectChanges();

      expect(title()).toBe("Token Successfully Enrolled");
      expect(harness.element.querySelector(".pi-dialog")).toBe(wrapper);
      expect(dialogService.openDialog).not.toHaveBeenCalled();
    });

    it("offers Retry next to Close after a failed FIDO2 registration", async () => {
      allowDelete(false);
      open(
        response({ rollout_state: "clientwait" }),
        { tokenType: "webauthn" },
        {
          kind: "fido2",
          register: () => Promise.resolve(null)
        }
      );
      await new Promise((resolve) => setTimeout(resolve));
      harness.fixture.detectChanges();

      expect(harness.step()).toBeInstanceOf(TokenCompleteEnrollmentFido2Component);
      expect(footerLabels()).toEqual(["Close", "Retry"]);
    });

    it("warns in the push step that the token is deleted even if the QR code was scanned", () => {
      allowDelete(true);
      tokenService.pollTokenRolloutState.mockReturnValue(new Subject());
      open(response({ rollout_state: "clientwait" }), {}, { kind: "push" });
      answer(undefined);

      harness.footerButton("Close")!.click();

      const message = dialogService.openDialog.mock.calls[0][0].data.message as string;
      expect(message).toContain("The token is deleted even if the QR code was already scanned.");
    });

    it("moves the focus to the input of a new step, else to its title", async () => {
      allowDelete(false);
      open(twoStep());
      harness.fixture.autoDetectChanges();
      await harness.fixture.whenStable();
      expect(document.activeElement?.tagName).toBe("INPUT");

      harness.flow.finishStep(enrolled());
      await harness.fixture.whenStable();
      expect(document.activeElement?.textContent?.trim()).toBe("Token Successfully Enrolled");
    });

    it("offers the step's action next to Close", () => {
      allowDelete(true);
      open(twoStep());

      expect(footerLabels()).toEqual(["Close", "Enroll"]);
    });
  });

  describe("leaving an unfinished step with the delete right", () => {
    beforeEach(() => {
      allowDelete(true);
      open(verify());
    });

    it("asks whether to keep or delete the token", () => {
      answer(undefined);

      harness.footerButton("Close")?.click();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ title: "Leave Incomplete Enrollment", discardButtonText: "Delete Token" })
        })
      );
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
      expect(harness.element.textContent).not.toContain("If you close the dialog now");
    });

    it("keeps the token for the reopen button", () => {
      answer("save-exit");

      harness.footerButton("Close")?.click();

      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).toHaveBeenCalled();
      expect(options.onIncomplete).toHaveBeenCalled();
    });

    it("deletes the token", () => {
      answer("discard");

      harness.footerButton("Close")?.click();

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("OATH0001");
      expect(harness.dialogRef.close).toHaveBeenCalled();
      expect(options.onCancelled).toHaveBeenCalled();
      expect(options.onIncomplete).not.toHaveBeenCalled();
    });

    it("does not show the success step when the step finishes while the token is being deleted", () => {
      const deletion = new Subject<void>();
      tokenService.cancelEnrollment.mockReturnValue(deletion);
      answer("discard");
      harness.footerButton("Close")?.click();

      harness.flow.finishStep(enrolled());
      harness.fixture.detectChanges();
      expect(harness.step()).toBeInstanceOf(TokenVerifyEnrollmentComponent);
      deletion.next();
      deletion.complete();

      expect(harness.dialogRef.close).toHaveBeenCalled();
      expect(options.onCancelled).toHaveBeenCalled();
      expect(harness.flow.step()).toBe("verify");
    });

    it("lets Escape and a backdrop click ask the same way", () => {
      answer(undefined);
      expect(harness.dialogRef.disableClose).toBe(true);

      harness.dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      harness.dialogRef.fireBackdropClick();

      expect(dialogService.openDialog).toHaveBeenCalledTimes(2);
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });

    it("closes an unanswered question once the step is done", () => {
      const questionRef = new MockMatDialogRef();
      dialogService.openDialog.mockReturnValue(questionRef);
      harness.footerButton("Close")?.click();

      harness.flow.finishStep(enrolled());

      expect(questionRef.close).toHaveBeenCalled();
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });

    it("deletes the token and stays on the enrollment page when its own link was followed", () => {
      answer("discard");
      const contentService = TestBed.inject(ContentService) as unknown as MockContentService;

      (harness.element.querySelector(".enrolled__card-value") as HTMLElement).click();

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("OATH0001");
      expect(contentService.tokenSelected).not.toHaveBeenCalled();
    });

    it("follows a link to another page after keeping the token", async () => {
      answer("save-exit");
      const confirmLeave = harness.fixture.componentInstance["confirmLeave"];
      let followed: boolean | undefined;

      confirmLeave("user").subscribe((result) => (followed = result));

      expect(followed).toBe(true);
      expect(harness.dialogRef.close).toHaveBeenCalled();
    });
  });

  describe("leaving an unfinished step without a choice", () => {
    it("closes right away without the delete right and says how to finish the token", () => {
      allowDelete(false);
      open(verify());

      expect(harness.element.textContent).toContain(
        "you can open it again with the Reopen enrollment dialog button next to Enroll Token"
      );
      harness.footerButton("Close")?.click();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).toHaveBeenCalled();
      expect(options.onIncomplete).toHaveBeenCalled();
    });

    describe("in a FIDO2 registration, which cannot be reopened", () => {
      const fido2 = (tokenType: string) =>
        open(
          response({ rollout_state: "clientwait" }),
          { tokenType },
          { kind: "fido2", register: () => new Promise(() => undefined) }
        );
      const allow = (rights: string[], rolloverTypes: string[] = []) => {
        authService.actionAllowed.mockImplementation((action: string) => rights.includes(action));
        authService.authData.set({
          ...authService.authData()!,
          token_rollover: Object.fromEntries(rolloverTypes.map((type) => [type, []]))
        });
      };

      it("says that a passkey cannot be finished, as a passkey cannot be rolled over", () => {
        allow(["token_rollover"], ["passkey"]);
        fido2("passkey");

        expect(harness.element.textContent).toContain(
          "the token cannot be finished. Ask an administrator to delete it."
        );
        expect(harness.element.textContent).not.toContain("Reopen enrollment dialog");
      });

      it("points to the rollover for a WebAuthn token the user may roll over", () => {
        allow(["token_rollover"], ["webauthn"]);
        fido2("webauthn");

        expect(harness.element.textContent).toContain("roll the token over in its details to finish it");
      });

      it("says that a WebAuthn token cannot be finished without the rollover right", () => {
        allow([], ["webauthn"]);
        fido2("webauthn");

        expect(harness.element.textContent).toContain("the token cannot be finished");
      });
    });

    it("never deletes in a rollover", () => {
      allowDelete(true);
      open(verify(), { rollover: true });

      expect(harness.element.textContent).toContain("roll the token over again");
      harness.dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Escape" }));

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).toHaveBeenCalled();
    });
  });

  describe("context", () => {
    const withUser = { enrollParameters: { data: { user: "alice", realm: "realm1" } } as EnrollTokenArguments };
    const setRole = (role: "admin" | "user") =>
      authService.authData.set({ ...authService.authData(), role } as AuthData);
    const cardLabels = () =>
      Array.from(harness.element.querySelectorAll(".enrolled__card-label") as NodeListOf<HTMLElement>).map((label) =>
        label.textContent?.trim()
      );

    it("shows the user and the realm to an admin", () => {
      setRole("admin");
      open(twoStep(), withUser);

      expect(harness.element.textContent).toContain("The token was created, but its enrollment is not complete yet.");
      expect(cardLabels()).toEqual(["Token", "User", "Realm"]);
    });

    it("shows the container the server added the token to, also on the success step", () => {
      setRole("admin");
      open(response({ rollout_state: "verify", verify: { message: "Enter OTP" }, container_serial: "CONT0001" }));
      expect(cardLabels()).toEqual(["Token", "Container"]);

      harness.flow.finishStep(enrolled());
      harness.fixture.detectChanges();
      expect(cardLabels()).toEqual(["Token", "Container"]);
    });

    it("shows no container the server did not add the token to", () => {
      setRole("admin");
      open(enrolled(), {
        enrollParameters: { data: { containerSerial: "CONT0001" } } as unknown as EnrollTokenArguments
      });

      expect(cardLabels()).toEqual(["Token"]);
    });

    it("leaves out the user and the realm in self-service", () => {
      setRole("user");
      open(twoStep(), withUser);

      expect(cardLabels()).toEqual(["Token"]);
    });

    it("frames every step with the summary and the post customization in the wizard", async () => {
      setRole("user");
      open(verify(), { ...withUser, wizard: true });
      const httpMock = TestBed.inject(HttpTestingController);
      const customizationUrl = (position: string) =>
        environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;
      httpMock.expectOne(customizationUrl("top")).flush("<p>Top {{ serial }}</p>");
      httpMock.expectOne(customizationUrl("bottom")).flush("<p>Bottom</p>");
      await harness.fixture.whenStable();
      harness.fixture.detectChanges();

      const text = harness.element.textContent as string;
      expect(text).toContain("Top OATH0001");
      expect(text).toContain("Bottom");
      expect(cardLabels()).toEqual([]);
      httpMock.verify();
    });

    it("cannot be closed on the wizard's success step", () => {
      options = { ...options, successStep: () => TokenEnrollmentSuccessWizardComponent };
      open(enrolled(), { wizard: true });

      harness.dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      harness.dialogRef.fireBackdropClick();

      expect(footerLabels()).toEqual(["Logout"]);
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });
  });

  it("stops polling once it closes", () => {
    open(enrolled());

    harness.footerButton("Close")?.click();

    expect(tokenService.stopPolling).toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    allowDelete(true);
    open(twoStep());

    expect(await axe(harness.element)).toHaveNoViolations();
  });
});
