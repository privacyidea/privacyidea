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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrolledTextLink } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { lastValueFrom, NEVER, of, Subject, throwError } from "rxjs";
import {
  TokenEnrollmentFirstStepDialogComponent,
  TokenEnrollmentFirstStepDialogData
} from "./token-enrollment-first-step-dialog.component";
import { axe } from "@testing/axe";

describe("TokenEnrollmentFirstStepDialogComponent", () => {
  let component: TokenEnrollmentFirstStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentFirstStepDialogComponent>;
  let tokenService: MockTokenService;
  let dialogService: MockDialogService;
  let dialogRefMock: jest.Mocked<MatDialogRef<TokenEnrollmentFirstStepDialogComponent>>;

  const enrollmentResponse = {
    detail: {
      rollout_state: "clientwait",
      serial: "PIPU0001",
      pushurl: {
        description: "Push URL",
        img: "push.png",
        value: "https://example.com/push",
        value_b32: "B32VALUE"
      }
    }
  } as unknown as EnrollmentResponse;

  const setup = async (data: Partial<TokenEnrollmentFirstStepDialogData> = {}) => {
    TestBed.resetTestingModule();
    dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(NEVER)
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentFirstStepDialogComponent>>;

    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: { enrollmentResponse, ...data } },
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService }
      ],
      imports: [TokenEnrollmentFirstStepDialogComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentFirstStepDialogComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  };

  const footerButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));

  const buttonLabels = (): string[] => footerButtons().map((button) => button.textContent?.trim() ?? "");

  const clickButton = (label: string) => {
    const button = footerButtons().find((candidate) => candidate.textContent?.trim() === label);
    expect(button).toBeTruthy();
    button!.click();
    fixture.detectChanges();
  };

  it("should create", async () => {
    await setup();
    expect(component).toBeTruthy();
  });

  describe("button visibility", () => {
    it("shows only the close button when the caller offers nothing else", async () => {
      await setup();
      expect(buttonLabels()).toEqual(["Close"]);
    });

    it("replaces the close button with cancel when the caller allows cancelling", async () => {
      await setup({ showCancelButton: true });
      expect(buttonLabels()).toEqual(["Cancel"]);
    });

    it("offers retry only once an attempt has failed", async () => {
      const registrationFailed = signal(false);
      await setup({ showCancelButton: true, registrationFailed, onRetry: jest.fn() });
      expect(buttonLabels()).toEqual(["Cancel"]);

      registrationFailed.set(true);
      fixture.detectChanges();
      expect(buttonLabels()).toEqual(["Cancel", "Retry"]);
    });

    it("does not offer retry without a retry handler", async () => {
      await setup({ showCancelButton: true, registrationFailed: signal(true) });
      expect(buttonLabels()).not.toContain("Retry");
    });
  });

  describe("header and leaving through a link", () => {
    const answer = (result: string | undefined) => {
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(result));
      dialogService.openDialog.mockReturnValue(confirmationRef);
    };
    const confirmLeave = (link: EnrolledTextLink = "token") => lastValueFrom(component["confirmLeave"](link));

    it("shows the incomplete summary with the user of the enrollment", async () => {
      await setup({ enrollmentData: { type: "push", user: "alice", realm: "realm1" } });
      const text = fixture.nativeElement.textContent as string;
      expect(text).toContain("The token was created, but its enrollment is not complete yet.");
      expect(text).toContain("alice");
      expect(text).not.toContain("is not completely enrolled, yet");
    });

    it("leaves like Close while only Close is offered", async () => {
      await setup();

      expect(await confirmLeave()).toBe(true);
      expect(dialogRefMock.close).toHaveBeenCalledWith(undefined);
      expect(dialogService.openDialog).not.toHaveBeenCalled();
    });

    it("deletes the token and stays on the enrollment page when its own link was followed", async () => {
      await setup({ showCancelButton: true });
      answer("discard");

      expect(await confirmLeave("token")).toBe(false);

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("drops the question and keeps the token once the rollout closes the step", async () => {
      await setup({ showCancelButton: true });
      const stepClosed = new Subject<void>();
      dialogRefMock.afterClosed.mockReturnValue(stepClosed);
      const followed = confirmLeave("container");
      const questionRef = dialogService.openDialog.mock.results[0].value as MockMatDialogRef<unknown>;

      stepClosed.next();

      expect(questionRef.close).toHaveBeenCalled();
      expect(await followed).toBe(false);
      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
    });

    it("deletes the token and follows a link to another page", async () => {
      await setup({ showCancelButton: true });
      answer("discard");

      expect(await confirmLeave("user")).toBe(true);

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("keeps the token when the user chooses to while only Cancel is offered", async () => {
      await setup({ showCancelButton: true });
      answer("save-exit");

      expect(await confirmLeave()).toBe(true);

      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalledWith(undefined);
    });

    it("stays when the user cancels while only Cancel is offered", async () => {
      await setup({ showCancelButton: true });
      answer(undefined);

      expect(await confirmLeave()).toBe(false);
    });
  });

  describe("wizard", () => {
    const customizationUrl = (position: string) =>
      environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;

    it("frames the step with the post customization", async () => {
      await setup({ wizard: true });
      const httpMock = TestBed.inject(HttpTestingController);
      httpMock.expectOne(customizationUrl("top")).flush("<p>Top {{ serial }}</p>");
      httpMock.expectOne(customizationUrl("bottom")).flush("<p>Bottom</p>");
      await fixture.whenStable();
      fixture.detectChanges();

      const text = fixture.nativeElement.textContent as string;
      expect(text).toContain("Top PIPU0001");
      expect(text).toContain("Bottom");
      expect(buttonLabels()).toEqual(["Close"]);
      httpMock.verify();
    });

    it("loads no customization outside the wizard", async () => {
      await setup();
      TestBed.inject(HttpTestingController).verify();
    });
  });

  describe("cancelling the enrollment", () => {
    it("deletes the incomplete token and reports the cancellation", async () => {
      await setup({ showCancelButton: true });

      clickButton("Cancel");

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("keeps the dialog open when the deletion fails", async () => {
      await setup({ showCancelButton: true });
      tokenService.cancelEnrollment.mockReturnValue(throwError(() => new Error("denied")));

      clickButton("Cancel");

      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("asks for confirmation first when the caller provides a message", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(true));
      dialogService.openDialog.mockReturnValue(confirmationRef);

      clickButton("Cancel");

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ message: "Scanned codes stop working." })
        })
      );
      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
      expect(dialogRefMock.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("keeps the token when the confirmation is declined", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(false));
      dialogService.openDialog.mockReturnValue(confirmationRef);

      clickButton("Cancel");

      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
      expect(dialogRefMock.close).not.toHaveBeenCalled();
    });

    it("closes the unanswered confirmation once the rollout closes the step", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const stepClosed = new Subject<void>();
      dialogRefMock.afterClosed.mockReturnValue(stepClosed);

      clickButton("Cancel");
      const confirmationRef = dialogService.openDialog.mock.results[0].value as MockMatDialogRef<unknown>;
      stepClosed.next();

      expect(confirmationRef.close).toHaveBeenCalled();
      expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
    });

    it("completes a confirmed deletion even when the rollout closes the step meanwhile", async () => {
      await setup({ showCancelButton: true, cancelConfirmationMessage: "Scanned codes stop working." });
      const stepClosed = new Subject<void>();
      dialogRefMock.afterClosed.mockReturnValue(stepClosed);
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(true));
      dialogService.openDialog.mockReturnValue(confirmationRef);

      clickButton("Cancel");
      stepClosed.next();

      expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("PIPU0001");
    });
  });

  it("delegates retry to the caller", async () => {
    const onRetry = jest.fn();
    await setup({ registrationFailed: signal(true), onRetry });

    clickButton("Retry");

    expect(onRetry).toHaveBeenCalled();
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    await setup();
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
