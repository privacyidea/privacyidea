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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { SystemConfigComponent } from "./system-config.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideRouter, Router } from "@angular/router";
import { provideLocationMocks } from "@angular/common/testing";
import { of } from "rxjs";
import { SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { AuthService } from "../../../services/auth/auth.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { ContentService } from "../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../route_paths";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";
import { MockContentService } from "../../../../testing/mock-services";
import { MockNotificationService } from "../../../../testing/mock-services";
import { MockSystemService } from "../../../../testing/mock-services/mock-system-service";
import { MockPiResponse } from "../../../../testing/mock-services";
import { MatSnackBar } from "@angular/material/snack-bar";

describe("SystemConfigComponent", () => {
  let component: SystemConfigComponent;
  let fixture: ComponentFixture<SystemConfigComponent>;
  let systemService: MockSystemService;
  let authService: MockAuthService;
  let notificationService: MockNotificationService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SystemConfigComponent],
      providers: [
        provideRouter([]),
        provideLocationMocks(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatSnackBar, useValue: { open: jest.fn() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SystemConfigComponent);
    component = fixture.componentInstance;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    router = TestBed.inject(Router);

    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    contentService.routeUrl.set(ROUTE_PATHS.CONFIGURATION_SYSTEM);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should load system config on init", () => {
    expect(component.params).toBeDefined();
    expect(component.params.splitAtSign).toBe(true);
    expect(component.params.IncFailCountOnFalsePin).toBe(false);
    expect(component.params.no_auth_counter).toBe(true);
    expect(component.params.PrependPin).toBe(false);
    expect(component.params.ReturnSamlAttributes).toBe(true);
    expect(component.params.ReturnSamlAttributesOnFail).toBe(false);
    expect(component.params.AutoResync).toBe(true);
    expect(component.params.UiLoginDisplayHelpButton).toBe(false);
    expect(component.params.UiLoginDisplayRealmBox).toBe(true);
    expect(component.params.someOtherConfig).toBe("test_value");
  });

  it("should convert boolean config values correctly", () => {
    // Test that boolean values are properly converted
    expect(component.params.splitAtSign).toBe(true);
    expect(component.params.IncFailCountOnFalsePin).toBe(false);
    expect(component.params.no_auth_counter).toBe(true);
    expect(component.params.PrependPin).toBe(false);
    expect(component.params.ReturnSamlAttributes).toBe(true);
    expect(component.params.ReturnSamlAttributesOnFail).toBe(false);
    expect(component.params.AutoResync).toBe(true);
    expect(component.params.UiLoginDisplayHelpButton).toBe(false);
    expect(component.params.UiLoginDisplayRealmBox).toBe(true);
  });

  it("should load SMTP identifiers on init", () => {
    expect(component.smtpIdentifiers).toBeDefined();
    expect(Array.isArray(component.smtpIdentifiers)).toBe(true);
  });

  it("should save system config successfully", () => {
    const saveSpy = jest.spyOn(systemService, "saveSystemConfig");
    const notificationSpy = jest.spyOn(notificationService, "openSnackBar");

    component.saveSystemConfig();

    expect(saveSpy).toHaveBeenCalled();
    expect(notificationSpy).toHaveBeenCalledWith("System configuration saved successfully.");
  });

  it("should handle save system config error", () => {
    jest.spyOn(systemService, "saveSystemConfig").mockReturnValueOnce(
      of(new MockPiResponse<{ status: boolean }>({ result: { status: false } }))
    );
    const notificationSpy = jest.spyOn(notificationService, "openSnackBar");

    component.saveSystemConfig();

    expect(notificationSpy).toHaveBeenCalledWith("Failed to save system configuration.");
  });

  it("should delete user cache successfully", () => {
    const deleteSpy = jest.spyOn(systemService, "deleteUserCache");
    const notificationSpy = jest.spyOn(notificationService, "openSnackBar");

    component.deleteUserCache();

    expect(deleteSpy).toHaveBeenCalled();
    expect(notificationSpy).toHaveBeenCalledWith("User cache deleted successfully.");
  });

  it("should handle delete user cache error", () => {
    jest.spyOn(systemService, "deleteUserCache").mockReturnValueOnce(
      of(new MockPiResponse<{ status: boolean }>({ result: { status: false } }))
    );
    const notificationSpy = jest.spyOn(notificationService, "openSnackBar");

    component.deleteUserCache();

    expect(notificationSpy).toHaveBeenCalledWith("Failed to delete user cache.");
  });

  it("should check config write permission", () => {
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    expect(component.hasConfigWritePermission()).toBe(true);

    jest.spyOn(authService, "actionAllowed").mockReturnValue(false);
    expect(component.hasConfigWritePermission()).toBe(false);
  });

  it("should convert various truthy values to boolean correctly", () => {
    const testCases = [
      { input: true, expected: true },
      { input: 1, expected: true },
      { input: "1", expected: true },
      { input: "True", expected: true },
      { input: "true", expected: true },
      { input: "TRUE", expected: true },
      { input: false, expected: false },
      { input: 0, expected: false },
      { input: "0", expected: false },
      { input: "False", expected: false },
      { input: "false", expected: false },
      { input: "FALSE", expected: false },
      { input: "other", expected: false },
      { input: null, expected: false },
      { input: undefined, expected: false }
    ];

    testCases.forEach(({ input, expected }) => {
      expect(component.isChecked(input)).toBe(expected);
    });
  });

  it("should reload system config when loadSystemConfig is called", () => {
    const reloadSpy = jest.spyOn(systemService.systemConfigResource, "reload");
    component.loadSystemConfig();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should load SMTP identifiers when loadSmtpIdentifiers is called", () => {
    const loadSpy = jest.spyOn(systemService, "loadSmtpIdentifiers");
    component.loadSmtpIdentifiers();
    expect(loadSpy).toHaveBeenCalled();
  });
});