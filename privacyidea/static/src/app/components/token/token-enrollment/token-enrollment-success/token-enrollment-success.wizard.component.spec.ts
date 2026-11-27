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
import { Router } from "@angular/router";
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TokenEnrollmentDialogData, TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { EnrollmentDialogHarness } from "@testing/enrollment-dialog-harness";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";
import { TokenEnrollmentSuccessWizardComponent } from "./token-enrollment-success.wizard.component";

describe("TokenEnrollmentSuccessWizardComponent", () => {
  let component: TokenEnrollmentSuccessWizardComponent;
  let harness: EnrollmentDialogHarness;
  let authService: MockAuthService;
  let httpMock: HttpTestingController;

  const response = (): EnrollmentResponse => ({
    type: "totp",
    detail: {
      type: "totp",
      serial: "1234567890",
      googleurl: {
        description: "Google Authenticator URL",
        img: "",
        value: "otpauth://totp/Example:user?secret=ABCDEF1234567890&issuer=Example"
      }
    },
    result: { status: true }
  });
  const dialogData = (): Partial<TokenEnrollmentDialogData> => ({
    tokenType: "totp",
    wizard: true,
    enrollParameters: {
      data: { user: "alice", realm: "realm1" } as unknown as TokenEnrollmentData,
      mapper: {} as unknown as BaseApiPayloadMapper
    }
  });
  const customizationUrl = (position: string) =>
    environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;

  const setup = async (containerWizard = false) => {
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
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.authData.set({
      ...authService.authData(),
      role: "user",
      container_wizard: { enabled: containerWizard, type: "", registration: false, template: null }
    } as AuthData);
    httpMock = TestBed.inject(HttpTestingController);
    harness.open(response(), dialogData(), { successStep: () => TokenEnrollmentSuccessWizardComponent });
    component = harness.step<TokenEnrollmentSuccessWizardComponent>();
  };

  const flushCustomization = async (top = "", bottom = "") => {
    httpMock.expectOne(customizationUrl("top")).flush(top);
    httpMock.expectOne(customizationUrl("bottom")).flush(bottom);
    await harness.fixture.whenStable();
    harness.fixture.detectChanges();
  };

  const footerButtons = () => harness.footerButtons();
  const footerButton = (label: string) => harness.footerButton(label);

  afterEach(() => httpMock.verify());

  it("frames the enrollment data with the summary and the post customization", async () => {
    await setup();
    await flushCustomization("<p>Top {{ serial }}</p>", "<p>Bottom</p>");

    const text = harness.element.textContent as string;
    expect(text).toContain("The token has been successfully enrolled.");
    expect(text).toContain("Top 1234567890");
    expect(text).toContain("Bottom");
    expect(harness.element.querySelector(".enrolled__cards")).toBeNull();
  });

  it("shows the reduced enrollment data", async () => {
    await setup();
    await flushCustomization();

    expect(harness.element.querySelector("app-token-enrollment-data")).toBeTruthy();
    expect(harness.element.querySelector("app-qr-code-text")).toBeNull();
    expect(harness.element.textContent).not.toContain("Regenerate");
  });

  it("offers only create container and logout", async () => {
    await setup(true);
    await flushCustomization();

    expect(footerButtons().map((button) => button.textContent?.trim())).toEqual(["Create Container", "Logout"]);
  });

  it("cannot be closed", async () => {
    await setup();
    await flushCustomization();
    const dialogRef = harness.dialogRef;

    dialogRef.fireKeydownEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    dialogRef.fireBackdropClick();

    expect(dialogRef.disableClose).toBe(true);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  describe("unsaved data", () => {
    const unsaved = "Download the PKCS#12 file.";
    let dialogService: MockDialogService;

    const answerConfirmation = (confirmed: boolean) => {
      const confirmationRef = new MockMatDialogRef();
      confirmationRef.afterClosed.mockReturnValue(of(confirmed));
      dialogService.openDialog.mockReturnValue(confirmationRef);
    };

    beforeEach(async () => {
      await setup(true);
      await flushCustomization();
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      dialogService.openDialog.mockClear();
    });

    it("keeps logout and create container enabled", () => {
      component.onCloseConfirmationChange(unsaved);
      harness.fixture.detectChanges();

      expect(footerButtons().every((button) => !button.disabled)).toBe(true);
    });

    it("logs out right away when nothing is left to save", () => {
      footerButton("Logout")?.click();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(authService.logout).toHaveBeenCalled();
    });

    it("asks before logging out and stays when not confirmed", () => {
      component.onCloseConfirmationChange(unsaved);
      answerConfirmation(false);

      footerButton("Logout")?.click();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            title: "Enrollment Data Not Saved",
            message: unsaved,
            confirmAction: expect.objectContaining({ label: "Logout" })
          })
        })
      );
      expect(authService.logout).not.toHaveBeenCalled();
    });

    it("logs out once confirmed", () => {
      component.onCloseConfirmationChange(unsaved);
      answerConfirmation(true);

      footerButton("Logout")?.click();

      expect(authService.logout).toHaveBeenCalled();
    });

    it("asks before opening the container wizard", () => {
      const navigate = jest.spyOn(TestBed.inject(Router), "navigate").mockResolvedValue(true);
      component.onCloseConfirmationChange(unsaved);
      answerConfirmation(false);

      footerButton("Create Container")?.click();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ confirmAction: expect.objectContaining({ label: "Create Container" }) })
        })
      );
      expect(navigate).not.toHaveBeenCalled();
      expect(harness.dialogRef.close).not.toHaveBeenCalled();
    });
  });

  it("closes the dialog and opens the container wizard on create container", async () => {
    await setup(true);
    await flushCustomization();
    const navigate = jest.spyOn(TestBed.inject(Router), "navigate").mockResolvedValue(true);

    footerButton("Create Container")?.click();

    expect(harness.dialogRef.close).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith([ROUTE_PATHS.CONTAINERS_WIZARD]);
  });

  it("passes the axe accessibility checks", async () => {
    await setup();
    await flushCustomization();

    expect(await axe(harness.element)).toHaveNoViolations();
  });
});
