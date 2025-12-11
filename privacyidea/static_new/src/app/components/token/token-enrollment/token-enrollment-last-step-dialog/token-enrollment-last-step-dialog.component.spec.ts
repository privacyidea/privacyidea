/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { provideExperimentalZonelessChangeDetection, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of, Subject } from "rxjs";
import {
  TokenEnrollmentLastStepDialogComponent,
  TokenEnrollmentLastStepDialogData
} from "./token-enrollment-last-step-dialog.component";
import { TokenEnrollmentLastStepDialogSelfServiceComponent } from "./token-enrollment-last-step-dialog.self-service.component";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData } from "../../../../services/user/user.service";
import { TokenEnrollmentLastStepDialogWizardComponent } from "./token-enrollment-last-step-dialog.wizard.component";
import { HttpClient, provideHttpClient } from "@angular/common/http";
import { AuthService } from "../../../../services/auth/auth.service";
import { MockLocalService, MockNotificationService } from "../../../../../testing/mock-services";
import { LocalService } from "../../../../services/local/local.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { ActivatedRoute, Router } from "@angular/router";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";

const buildBaseData = (): TokenEnrollmentLastStepDialogData => ({
  tokentype: { key: "hotp", name: "HOTP", text: "HOTP Token", info: "" },
  response: {
    detail: {
      serial: "HOTP123456",
      googleurl: {
        img: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60eADwAAAABJRU5ErkJggg==",
        value: "otpauth://hotp/test",
        description: "test url"
      }
    }
  } as any,
  serial: signal<string | null>(null),
  enrollToken: jest.fn(),
  user: { username: "testuser" } as UserData,
  userRealm: "testrealm",
  onlyAddToRealm: false
});

const detectChangesStable = async (fixture: ComponentFixture<any>) => {
  fixture.detectChanges();
  await Promise.resolve();
  fixture.detectChanges();
};

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  let dialogRef: jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;
  let tokenService: jest.Mocked<TokenServiceInterface>;
  let contentService: jest.Mocked<ContentServiceInterface>;
  let mockDialogData: TokenEnrollmentLastStepDialogData;
  let afterClosedSubject: Subject<void>;

  beforeEach(async () => {
    mockDialogData = buildBaseData();
    afterClosedSubject = new Subject<void>();

    const dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(afterClosedSubject.asObservable())
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogComponent>>;
    const tokenServiceMock = { stopPolling: jest.fn() } as unknown as jest.Mocked<TokenServiceInterface>;
    const contentServiceMock = {
      tokenSelected: jest.fn(),
      containerSelected: jest.fn()
    } as unknown as jest.Mocked<ContentServiceInterface>;

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogComponent, NoopAnimationsModule],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as any;
    tokenService = TestBed.inject(TokenService) as any;
    contentService = TestBed.inject(ContentService) as any;
  });

  it("should create", async () => {
    await detectChangesStable(fixture);
    expect(component).toBeTruthy();
  });

  it("should stop polling when the dialog is closed", async () => {
    await detectChangesStable(fixture);
    afterClosedSubject.next();
    afterClosedSubject.complete();
    expect(tokenService.stopPolling).toHaveBeenCalled();
  });

  describe("UI display logic", () => {
    it("should show QR code for hotp", async () => {
      await detectChangesStable(fixture);
      expect(component.showQRCode()).toBe(true);
    });

    it("should NOT show QR code for sms", async () => {
      component.data.tokentype = { key: "sms", text: "SMS Token", info: "" } as any;
      await detectChangesStable(fixture);
      expect(component.showQRCode()).toBe(false);
    });

    it("should show regenerate button for hotp", async () => {
      await detectChangesStable(fixture);
      expect(component.showRegenerateButton()).toBe(true);
    });

    it.skip("should NOT show regenerate button for `sms` token", async () => {
      component.data.tokentype = { key: "sms", name: "SMS", text: "SMS Token", info: "" };
      await detectChangesStable(fixture);
      expect(component.showRegenerateButton()).toBe(false);
    });

    it("should display OTP values for paper tokens", async () => {
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" } as any;
      (component.data.response.detail as any)["otps"] = { "0": "123456", "1": "654321" };
      (component.data.response.detail as any).googleurl = undefined;
      await detectChangesStable(fixture);
      const otpElements = fixture.nativeElement.querySelectorAll(".otp-value");
      expect(otpElements.length).toBe(2);
      expect(otpElements[0].textContent).toContain("123456");
      expect(otpElements[1].textContent).toContain("654321");
    });

    it('should have regenerate button text "QR Code" for hotp', async () => {
      await detectChangesStable(fixture);
      expect(component.regenerateButtonText()).toBe("QR Code");
    });

    it('should have regenerate button text "Values" for paper', async () => {
      component.data.tokentype = { key: "paper", text: "Paper Token", info: "" } as any;
      await detectChangesStable(fixture);
      expect(component.regenerateButtonText()).toBe("Values");
    });
  });

  describe("User actions", () => {
    it("tokenSelected should close and notify", async () => {
      await detectChangesStable(fixture);
      const serial = "test-serial";
      component.tokenSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.tokenSelected).toHaveBeenCalledWith(serial);
    });

    it("containerSelected should close and notify", async () => {
      await detectChangesStable(fixture);
      const serial = "container-serial";
      component.containerSelected(serial);
      expect(dialogRef.close).toHaveBeenCalled();
      expect(contentService.containerSelected).toHaveBeenCalledWith(serial);
    });

    it("regenerateQRCode should re-enroll and close", async () => {
      await detectChangesStable(fixture);
      const serial = component.data.response.detail.serial as string;
      const enrollSpy = component.data.enrollToken;
      const serialSignalSpy = jest.spyOn(component.data.serial, "set");
      component.regenerateQRCode();
      expect(serialSignalSpy).toHaveBeenCalledWith(serial);
      expect(enrollSpy).toHaveBeenCalled();
      expect(serialSignalSpy).toHaveBeenCalledWith(null);
      expect(dialogRef.close).toHaveBeenCalled();
    });
  });
});

describe("TokenEnrollmentLastStepDialogSelfServiceComponent", () => {
  let component: TokenEnrollmentLastStepDialogSelfServiceComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogSelfServiceComponent>;
  let mockDialogData: TokenEnrollmentLastStepDialogData;

  beforeEach(async () => {
    mockDialogData = buildBaseData();
    const dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(new Subject<void>().asObservable())
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogSelfServiceComponent>>;
    const tokenServiceMock = { stopPolling: jest.fn() } as unknown as jest.Mocked<TokenServiceInterface>;
    const contentServiceMock = {
      tokenSelected: jest.fn(),
      containerSelected: jest.fn()
    } as unknown as jest.Mocked<ContentServiceInterface>;

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogSelfServiceComponent, NoopAnimationsModule],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogSelfServiceComponent);
    component = fixture.componentInstance;
  });

  it("should create", async () => {
    await detectChangesStable(fixture);
    expect(component).toBeTruthy();
  });
});

describe("TokenEnrollmentLastStepDialogWizardComponent", () => {
  let component: TokenEnrollmentLastStepDialogWizardComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogWizardComponent>;
  let mockDialogData: TokenEnrollmentLastStepDialogData;
  let authService: MockAuthService;
  let httpClientMock: any;

  beforeEach(async () => {
    mockDialogData = buildBaseData();
    httpClientMock = {
      get: jest.fn().mockReturnValue(of(""))
    };

    const dialogRefMock = {
      close: jest.fn(),
      afterClosed: jest.fn().mockReturnValue(new Subject<void>().asObservable())
    } as unknown as jest.Mocked<MatDialogRef<TokenEnrollmentLastStepDialogWizardComponent>>;
    const tokenServiceMock = { stopPolling: jest.fn() } as unknown as jest.Mocked<TokenServiceInterface>;
    const contentServiceMock = {
      tokenSelected: jest.fn(),
      containerSelected: jest.fn()
    } as unknown as jest.Mocked<ContentServiceInterface>;

    const routerMock = {
      navigateByUrl: jest.fn().mockResolvedValue(true),
      navigate: jest.fn().mockResolvedValue(true)
    };

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentLastStepDialogWizardComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideExperimentalZonelessChangeDetection(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: LocalService, useClass: MockLocalService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: HttpClient, useValue: httpClientMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogWizardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    jest.clearAllMocks();
  });

  it("should create", async () => {
    await detectChangesStable(fixture);
    expect(component).toBeTruthy();
  });

  it("shows Create Container button when containerWizard.enabled is true", async () => {
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { enabled: true, type: "generic", registration: false, template: null },
      token_wizard: true
    });
    fixture.detectChanges();
    await fixture.whenStable();
    const btn = fixture.nativeElement.querySelector("button");
    expect(btn?.textContent).toContain("Create Container");
    expect(btn?.textContent).not.toContain("Close");
    expect(btn?.textContent).not.toContain("Logout");
  });

  it("shows Logout button when containerWizard.enabled is false", async () => {
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { enabled: false, type: "generic", registration: false, template: null },
      token_wizard: true
    });
    fixture.detectChanges();
    await fixture.whenStable();
    const btn = fixture.nativeElement.querySelector("button");
    expect(btn?.textContent).toContain("Logout");
    expect(btn?.textContent).not.toContain("Create Container");
    expect(btn?.textContent).not.toContain("Close");
  });

  it("shows Logout button as long as tokenWizard is true, even if tokenWizard2nd id also true", async () => {
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { enabled: false, type: "generic", registration: false, template: null },
      token_wizard: true,
      token_wizard_2nd: true
    });
    fixture.detectChanges();
    await fixture.whenStable();
    const btn = fixture.nativeElement.querySelector("button");
    expect(btn?.textContent).toContain("Logout");
    expect(btn?.textContent).not.toContain("Create Container");
    expect(btn?.textContent).not.toContain("Close");
  });

  it("shows Close button when tokenWizard is false, but tokenWizard2nd is true", async () => {
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { enabled: false, type: "generic", registration: false, template: null },
      token_wizard: false,
      token_wizard_2nd: true
    });
    await detectChangesStable(fixture);
    const btn = fixture.nativeElement.querySelector("button");
    expect(btn?.textContent).toContain("Close");
    expect(btn?.textContent).not.toContain("Logout");
    expect(btn?.textContent).not.toContain("Create Container");
  });

  it("show loaded templates if not empty", async () => {
    authService.authData.set({
      ...authService.authData()!,
      token_wizard: true
    });
    httpClientMock.get.mockReturnValueOnce(of("Mock TOP HTML")).mockReturnValueOnce(of("Mock BOTTOM HTML"));
    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogWizardComponent);
    await detectChangesStable(fixture);
    expect(fixture.nativeElement.textContent).toContain("Mock TOP HTML");
    expect(fixture.nativeElement.textContent).toContain("Mock BOTTOM HTML");
    expect(fixture.nativeElement.textContent).not.toContain("Token successfully enrolled");
  });

  it("show default content if customization templates are empty", async () => {
    authService.authData.set({
      ...authService.authData()!,
      token_wizard: true
    });
    httpClientMock.get.mockReturnValue(of(""));
    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogWizardComponent);
    await detectChangesStable(fixture);
    expect(fixture.nativeElement.textContent).toContain("Token successfully enrolled");
  });
});
