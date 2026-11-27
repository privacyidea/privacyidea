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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { config as rxjsConfig, of } from "rxjs";
import { Type } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideRouter } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services";
import { TokenEnrollmentLastStepDialogWizardComponent } from "./token-enrollment-last-step-dialog.wizard.component";
import { ContentService } from "@services/content/content.service";
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TokenDetails, TokenEnrollmentDialogData, TokenService, Tokens } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockNotificationService, MockTokenService } from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { NotificationService } from "@services/notification/notification.service";
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { TokenEnrollmentLastStepDialogSelfServiceComponent } from "./token-enrollment-last-step-dialog.self-service.component";
import { axe } from "@testing/axe";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  const createDialogData = (): TokenEnrollmentDialogData => ({
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
    userRealm: "test-realm",
    onlyAddToRealm: false,
    enrollParameters: {
      data: {} as unknown as TokenEnrollmentData,
      mapper: {} as unknown as BaseApiPayloadMapper
    },
    onEnrollmentResponseChange: jest.fn()
  });

  const regeneratedResponse: EnrollmentResponse = {
    type: "totp",
    detail: {
      type: "totp",
      serial: "1234567890",
      googleurl: {
        description: "Google Authenticator URL",
        img: "regenerated-img",
        value: "otpauth://totp/Example:user?secret=REGENERATED&issuer=Example"
      }
    },
    result: { status: true }
  };

  const setup = async (
    dialogData: TokenEnrollmentDialogData,
    beforeCreate?: (tokenService: MockTokenService) => void
  ): Promise<void> => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogComponent],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: dialogData },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    beforeCreate?.(TestBed.inject(TokenService) as unknown as MockTokenService);
    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await setup(createDialogData());
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render title for normal enrollment", () => {
    expect(component["rollover"]).toBe(false);
    expect(component.title()).toBe("Token Successfully Enrolled");
  });

  it("should close on a route switch while nothing blocks it", () => {
    component.onSwitchRoute();

    expect(component["dialogRef"].close).toHaveBeenCalled();
  });

  it("should keep the dialog open on a route switch while closing is blocked", () => {
    component["onCloseBlockedReasonChange"]("Download the PKCS#12 file.");

    component.onSwitchRoute();

    expect(component["dialogRef"].close).not.toHaveBeenCalled();
  });

  it("should render the enrollment data when showEnrollData is not set", () => {
    expect(fixture.nativeElement.querySelector("app-token-enrollment-data")).toBeTruthy();
  });

  it("should not render the QR code when showEnrollData is false", async () => {
    const pushDialogData: TokenEnrollmentDialogData = {
      ...createDialogData(),
      showEnrollData: false,
      tokenType: "push",
      response: {
        type: "push",
        result: { status: true },
        detail: {
          type: "push",
          serial: "PIPU0001",
          pushurl: {
            description: "Push URL",
            img: "data:image/png;base64,qr",
            value: "otpauth://pipush/PIPU0001"
          }
        }
      }
    };
    await setup(pushDialogData);

    expect(fixture.nativeElement.querySelector("app-token-enrollment-data")).toBeNull();
    expect(fixture.nativeElement.querySelector('img[alt="QR Code"]')).toBeNull();
    expect(fixture.nativeElement.querySelector("app-token-enrolled-text")).toBeTruthy();
    expect(component.title()).toBe("Token Successfully Enrolled");
    expect(
      Array.from(fixture.nativeElement.querySelectorAll("button")).some((button) =>
        (button as HTMLButtonElement).textContent?.includes("Close")
      )
    ).toBe(true);
  });

  it("should report a regenerated QR code to the opener of the dialog", () => {
    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regeneratedResponse);

    expect(component.data.onEnrollmentResponseChange).toHaveBeenCalledWith(regeneratedResponse);
  });

  it("should render title for rollover", async () => {
    await setup({ ...createDialogData(), rollover: true });

    expect(component["rollover"]).toBe(true);
    expect(component.title()).toBe("Token Successfully Rolled Over");
  });

  describe("policy deviation note", () => {
    const hotpDialogData = (googleurl: string | null): TokenEnrollmentDialogData => ({
      ...createDialogData(),
      tokenType: "hotp",
      response: {
        type: "hotp",
        detail: {
          type: "hotp",
          serial: "OATH0001",
          ...(googleurl !== null && { googleurl: { description: "URL", img: "", value: googleurl } })
        },
        result: { status: true }
      },
      enrollParameters: {
        data: { type: "hotp", otpLength: 6, hashAlgorithm: "sha1" } as unknown as TokenEnrollmentData,
        mapper: {} as unknown as BaseApiPayloadMapper
      }
    });
    const tokenList = (tokens: Partial<TokenDetails>[]) =>
      MockPiResponse.fromValue<Tokens>({ count: tokens.length, current: 1, tokens: tokens as TokenDetails[] });
    const text = (): string => fixture.nativeElement.textContent ?? "";
    const render = async (): Promise<void> => {
      await fixture.whenStable();
      fixture.detectChanges();
    };

    it("shows the policy deviation note from the enrollment URL", async () => {
      await setup(hotpDialogData("otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=8&issuer=privacyIDEA"));
      await render();
      expect(text()).toContain("8 instead of 6");

      await setup(hotpDialogData("otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=6&issuer=privacyIDEA"));
      await render();
      expect(text()).not.toContain("instead of");
    });

    it("names the hash algorithm of a deviation", async () => {
      await setup(
        hotpDialogData("otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=6&algorithm=SHA256&issuer=privacyIDEA")
      );
      await render();

      expect(text()).toContain("hash algorithm sha256 instead of sha1");
    });

    it("shows both time steps of a deviation in the same unit", async () => {
      await setup({
        ...createDialogData(),
        tokenType: "daypassword",
        response: {
          type: "daypassword",
          detail: {
            type: "daypassword",
            serial: "DAYP0001",
            googleurl: {
              description: "URL",
              img: "",
              value:
                "otpauth://daypassword/DAYP0001?secret=ABC&algorithm=SHA256&period=7200&digits=6&issuer=privacyIDEA"
            }
          },
          result: { status: true }
        },
        enrollParameters: {
          data: {
            type: "daypassword",
            otpLength: 6,
            hashAlgorithm: "sha256",
            timeStep: "60m"
          } as unknown as TokenEnrollmentData,
          mapper: {} as unknown as BaseApiPayloadMapper
        }
      });
      await render();

      expect(text()).toContain("2h instead of 1h");
    });

    it("falls back to the token list without an enrollment URL", async () => {
      let tokenService!: MockTokenService;
      await setup(hotpDialogData(null), (service) => {
        tokenService = service;
        service.getTokenDetails.mockReturnValue(of(tokenList([{ otplen: 8, info: { hashlib: "sha1" } }])));
      });
      await render();

      expect(tokenService.getTokenDetails).toHaveBeenCalledWith("OATH0001");
      expect(text()).toContain("8 instead of 6");

      await setup(
        hotpDialogData("otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=6&issuer=privacyIDEA"),
        (service) => (tokenService = service)
      );
      await render();

      expect(tokenService.getTokenDetails).not.toHaveBeenCalled();
    });

    it("shows no note when the token list is empty", async () => {
      // An error thrown in a subscriber is reported asynchronously by rxjs and would not fail the test on its own.
      const unhandledError = jest.fn();
      const previousHandler = rxjsConfig.onUnhandledError;
      rxjsConfig.onUnhandledError = unhandledError;
      try {
        let tokenService!: MockTokenService;
        await setup(hotpDialogData(null), (service) => {
          tokenService = service;
          service.getTokenDetails.mockReturnValue(of(tokenList([])));
        });
        await render();
        await new Promise((resolve) => setTimeout(resolve));
        const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

        expect(tokenService.getTokenDetails).toHaveBeenCalledWith("OATH0001");
        expect(unhandledError).not.toHaveBeenCalled();
        expect(text()).not.toContain("instead of");
        expect(notificationService.error).not.toHaveBeenCalled();
        expect(notificationService.warning).not.toHaveBeenCalled();
      } finally {
        rxjsConfig.onUnhandledError = previousHandler;
      }
    });

    const renderVariant = async (variant: Type<unknown>): Promise<string> => {
      TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [variant],
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
          { provide: MatDialogRef, useClass: MockMatDialogRef },
          {
            provide: MAT_DIALOG_DATA,
            useValue: hotpDialogData("otpauth://hotp/OATH0001?secret=ABC&counter=1&digits=8&issuer=privacyIDEA")
          },
          { provide: ContentService, useClass: MockContentService },
          { provide: TokenService, useClass: MockTokenService },
          { provide: AuthService, useClass: MockAuthService },
          { provide: NotificationService, useClass: MockNotificationService }
        ]
      }).compileComponents();
      const variantFixture = TestBed.createComponent(variant);
      variantFixture.detectChanges();
      await variantFixture.whenStable();
      variantFixture.detectChanges();
      return variantFixture.nativeElement.textContent ?? "";
    };

    it("shows the policy deviation note in the self-service dialog", async () => {
      expect(await renderVariant(TokenEnrollmentLastStepDialogSelfServiceComponent)).toContain("8 instead of 6");
    });

    it("shows the policy deviation note in the wizard dialog", async () => {
      expect(await renderVariant(TokenEnrollmentLastStepDialogWizardComponent)).toContain("8 instead of 6");
    });
  });

  describe("self service", () => {
    let selfServiceFixture: ComponentFixture<TokenEnrollmentLastStepDialogSelfServiceComponent>;
    let dialogData: TokenEnrollmentDialogData;

    beforeEach(async () => {
      dialogData = createDialogData();
      TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [TokenEnrollmentLastStepDialogSelfServiceComponent],
        providers: [
          { provide: MatDialogRef, useClass: MockMatDialogRef },
          { provide: MAT_DIALOG_DATA, useValue: dialogData },
          { provide: ContentService, useClass: MockContentService },
          { provide: TokenService, useClass: MockTokenService }
        ]
      }).compileComponents();

      selfServiceFixture = TestBed.createComponent(TokenEnrollmentLastStepDialogSelfServiceComponent);
      selfServiceFixture.detectChanges();
    });

    it("should report a regenerated QR code to the opener of the dialog", () => {
      const enrollmentData = selfServiceFixture.debugElement.query(By.css("app-token-enrollment-data"));
      enrollmentData.triggerEventHandler("enrollmentResponseChange", regeneratedResponse);

      expect(dialogData.onEnrollmentResponseChange).toHaveBeenCalledWith(regeneratedResponse);
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
