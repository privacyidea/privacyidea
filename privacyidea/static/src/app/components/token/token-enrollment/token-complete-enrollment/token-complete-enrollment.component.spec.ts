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
import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrolledTextLink } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { DialogService } from "@services/dialog/dialog.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";

import { lastValueFrom, NEVER, of } from "rxjs";
import { TokenCompleteEnrollmentComponent } from "./token-complete-enrollment.component";
import { axe } from "@testing/axe";

describe("TokenCompleteEnrollmentComponent", () => {
  let component: TokenCompleteEnrollmentComponent;
  let fixture: ComponentFixture<TokenCompleteEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock; afterClosed: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123" }, type: "hotp" },
    enrollParameters: { data: { type: "hotp", twoStepInit: true } },
    onEnrollmentResponseChange: jest.fn()
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn(), afterClosed: jest.fn().mockReturnValue(NEVER) };
    await TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should report a regenerated QR code to the opener of the dialog", () => {
    const regenerated = {
      type: "hotp",
      detail: { type: "hotp", serial: "123", googleurl: { img: "regenerated-img", value: "regenerated-url" } },
      result: { status: true }
    } as EnrollmentResponse;
    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regenerated);

    expect(dialogData.onEnrollmentResponseChange).toHaveBeenCalledWith(regenerated);
  });

  it("shows the enrollment data for the type of the enrollment request", async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            tokenType: "totp",
            // A /token/init response has no top-level type
            response: { result: { status: true }, detail: { serial: "TOTP0001", rollout_state: "clientwait" } },
            enrollParameters: { data: { type: "totp", twoStepInit: true } },
            onEnrollmentResponseChange: jest.fn()
          }
        }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    const totpFixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
    totpFixture.detectChanges();

    const enrollmentData = totpFixture.debugElement.query(By.css("app-token-enrollment-data"));
    expect(enrollmentData.componentInstance.tokenType()).toBe("totp");
  });

  it("should disable enroll action if input is invalid", () => {
    component.clientPart.set("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("should enable enroll action if input is valid", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should call enrollToken and close dialog on successful enroll", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(
      of({
        type: "hotp",
        detail: { type: "hotp", serial: "X", rollout_state: "enrolled" },
        result: { status: true }
      } as EnrollmentResponse)
    );
    component.clientPart.set("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  it("should not close dialog if rollout_state is client_wait", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(
      of({
        type: "hotp",
        detail: { type: "hotp", serial: "X", rollout_state: "client_wait" },
        result: { status: true }
      } as EnrollmentResponse)
    );
    component.clientPart.set("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it("should remove twoStepInit from enrollParameters.data when enrolling", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    jest.spyOn(component["tokenService"], "enrollToken").mockImplementation((params) => {
      expect(params.data.type).toEqual("hotp");
      expect(params.data["twoStepInit"]).toBeUndefined();
      return of({
        result: { status: true },
        detail: { rollout_state: "enrolled", type: "hotp", serial: "123" },
        type: "hotp"
      });
    });
    component.onDialogAction("enroll");
  });

  describe("cancelling the enrollment", () => {
    let authService: MockAuthService;

    const setup = async (data: Record<string, unknown> = {}, canDelete = false) => {
      TestBed.resetTestingModule();
      dialogRefSpy = { close: jest.fn(), afterClosed: jest.fn().mockReturnValue(NEVER) };
      await TestBed.configureTestingModule({
        imports: [TokenCompleteEnrollmentComponent],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TokenService, useClass: MockTokenService },
          { provide: ContentService, useClass: MockContentService },
          { provide: AuthService, useClass: MockAuthService },
          { provide: DialogService, useClass: MockDialogService },
          { provide: MatDialogRef, useValue: dialogRefSpy },
          { provide: MAT_DIALOG_DATA, useValue: { ...dialogData, ...data } }
        ],
        schemas: [NO_ERRORS_SCHEMA]
      }).compileComponents();
      fixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
      component = fixture.componentInstance;
      mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.actionAllowed.mockImplementation((action: string) => canDelete && action === "delete");
      fixture.detectChanges();
    };

    const actionValues = () => component.dialogActions().map((action) => action.value);

    describe("leaving through a link", () => {
      const answer = (result: string | undefined) => {
        const confirmationRef = new MockMatDialogRef();
        confirmationRef.afterClosed.mockReturnValue(of(result));
        (TestBed.inject(DialogService) as unknown as MockDialogService).openDialog.mockReturnValue(confirmationRef);
      };
      const confirmLeave = (link: EnrolledTextLink = "token") => lastValueFrom(component["confirmLeave"](link));

      it("shows the header with the incomplete summary and the cards", async () => {
        await setup(
          { enrollParameters: { data: { type: "hotp", twoStepInit: true, user: "alice", realm: "realm1" } } },
          false
        );
        const text = fixture.nativeElement.textContent as string;
        expect(text).toContain("The token was created, but its enrollment is not complete yet.");
        expect(text).toContain("alice");
      });

      it("leaves like Close while only Close is offered", async () => {
        await setup({}, false);

        expect(await confirmLeave()).toBe(true);
        expect(dialogRefSpy.close).toHaveBeenCalledWith(undefined);
        expect((TestBed.inject(DialogService) as unknown as MockDialogService).openDialog).not.toHaveBeenCalled();
      });

      it("deletes the token and stays on the enrollment page when its own link was followed", async () => {
        await setup({}, true);
        answer("discard");

        expect(await confirmLeave("token")).toBe(false);

        expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
        expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
      });

      it("deletes the token and follows a link to another page", async () => {
        await setup({}, true);
        answer("discard");

        expect(await confirmLeave("user")).toBe(true);

        expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
        expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
      });

      it("keeps the token when the user chooses to while only Cancel is offered", async () => {
        await setup({}, true);
        answer("save-exit");

        expect(await confirmLeave()).toBe(true);

        expect(mockTokenService.cancelEnrollment).not.toHaveBeenCalled();
        expect(dialogRefSpy.close).toHaveBeenCalledWith(undefined);
      });

      it("stays when the user cancels while only Cancel is offered", async () => {
        await setup({}, true);
        answer(undefined);

        expect(await confirmLeave()).toBe(false);
        expect(mockTokenService.cancelEnrollment).not.toHaveBeenCalled();
      });
    });
    const buttonLabels = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button") as NodeListOf<HTMLElement>).map(
        (button) => button.textContent?.trim() ?? ""
      );

    it("offers close instead of cancel without the delete right", async () => {
      await setup({}, false);

      expect(actionValues()).toEqual(["enroll"]);
      expect(buttonLabels()).toEqual(["Close", "Enroll"]);
    });

    it("replaces the close button with cancel when the token may be deleted", async () => {
      await setup({ response: { detail: { serial: "123", "2step_output": 1 }, type: "hotp" } }, true);

      expect(actionValues()).toEqual(["cancelEnrollment", "enroll"]);
      expect(buttonLabels()).toEqual(["Cancel", "Enroll"]);
    });

    it("never offers to cancel a rollover", async () => {
      await setup({ rollover: true }, true);

      expect(actionValues()).toEqual(["enroll"]);
      expect(buttonLabels()).toEqual(["Close", "Enroll"]);
    });

    it("frames the step with the post customization in the wizard", async () => {
      await setup({ wizard: true }, true);
      const httpMock = TestBed.inject(HttpTestingController);
      const customizationUrl = (position: string) =>
        environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;
      httpMock.expectOne(customizationUrl("top")).flush("<p>Top {{ serial }}</p>");
      httpMock.expectOne(customizationUrl("bottom")).flush("<p>Bottom</p>");
      await fixture.whenStable();
      fixture.detectChanges();

      const text = fixture.nativeElement.textContent as string;
      expect(text).toContain("Top 123");
      expect(text).toContain("Bottom");
      httpMock.verify();
    });

    it("deletes the incomplete token and reports the cancellation", async () => {
      await setup({}, true);

      component.onDialogAction("cancelEnrollment");

      expect(mockTokenService.cancelEnrollment).toHaveBeenCalledWith("123");
      expect(dialogRefSpy.close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
