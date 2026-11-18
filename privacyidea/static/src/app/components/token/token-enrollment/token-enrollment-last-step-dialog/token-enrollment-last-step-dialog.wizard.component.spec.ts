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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { BaseApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TokenEnrollmentDialogData, TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { TokenEnrollmentLastStepDialogWizardComponent } from "./token-enrollment-last-step-dialog.wizard.component";

describe("TokenEnrollmentLastStepDialogWizardComponent", () => {
  let component: TokenEnrollmentLastStepDialogWizardComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogWizardComponent>;
  let authService: MockAuthService;
  let httpMock: HttpTestingController;

  const dialogData = (): TokenEnrollmentDialogData => ({
    response: {
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
    },
    tokenType: "totp",
    enrollParameters: {
      data: { user: "alice", realm: "realm1" } as unknown as TokenEnrollmentData,
      mapper: {} as unknown as BaseApiPayloadMapper
    }
  });
  const customizationUrl = (position: string) =>
    environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;

  const setup = async (containerWizard = false) => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogWizardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: dialogData() },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
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
    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogWizardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  const flushCustomization = async (top = "", bottom = "") => {
    httpMock.expectOne(customizationUrl("top")).flush(top);
    httpMock.expectOne(customizationUrl("bottom")).flush(bottom);
    await fixture.whenStable();
    fixture.detectChanges();
  };

  const footerButtons = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));
  const footerButton = (label: string) =>
    footerButtons().find((button) => button.textContent?.trim() === label) as HTMLButtonElement | undefined;

  afterEach(() => httpMock.verify());

  it("frames the enrollment data with the summary and the post customization", async () => {
    await setup();
    await flushCustomization("<p>Top {{ serial }}</p>", "<p>Bottom</p>");

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain("The token has been successfully enrolled.");
    expect(text).toContain("Top 1234567890");
    expect(text).toContain("Bottom");
    expect(fixture.nativeElement.querySelector(".enrolled__cards")).toBeNull();
  });

  it("shows the reduced enrollment data", async () => {
    await setup();
    await flushCustomization();

    expect(fixture.nativeElement.querySelector("app-token-enrollment-data")).toBeTruthy();
    expect(fixture.nativeElement.querySelector("app-qr-code-text")).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain("Regenerate");
  });

  it("offers only create container and logout", async () => {
    await setup(true);
    await flushCustomization();

    expect(footerButtons().map((button) => button.textContent?.trim())).toEqual(["Create Container", "Logout"]);
  });

  it("cannot be closed", async () => {
    await setup();
    await flushCustomization();

    expect(component["dialogRef"].disableClose).toBe(true);
  });

  it("enables logout only once nothing is left to save", async () => {
    await setup();
    await flushCustomization();
    component["onCloseBlockedReasonChange"]("Download the PKCS#12 file.");
    fixture.detectChanges();
    expect(footerButton("Logout")?.disabled).toBe(true);

    component["onCloseBlockedReasonChange"]("");
    fixture.detectChanges();
    footerButton("Logout")?.click();

    expect(authService.logout).toHaveBeenCalled();
  });

  it("closes the dialog and opens the container wizard on create container", async () => {
    await setup(true);
    await flushCustomization();
    const navigate = jest.spyOn(TestBed.inject(Router), "navigate").mockResolvedValue(true);

    footerButton("Create Container")?.click();

    expect(component["dialogRef"].close).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith([ROUTE_PATHS.CONTAINERS_WIZARD]);
  });

  it("passes the axe accessibility checks", async () => {
    await setup();
    await flushCustomization();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
