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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import {
    MockNotificationService,
    MockRealmService,
    MockTokenService,
    MockUserService
} from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { of } from "rxjs";
import { TokenImportComponent } from "./token-import.component";

describe("TokenImportComponent", () => {
  let component: TokenImportComponent;
  let fixture: ComponentFixture<TokenImportComponent>;
  let tokenService: MockTokenService;
  let notificationService: MockNotificationService;
  let pendingChangesService: MockPendingChangesService;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });

    class IO {
      observe = jest.fn();
      disconnect = jest.fn();

      constructor(_: any, __?: any) {}
    }

    (global as any).IntersectionObserver = IO;
  });

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenImportComponent, FormsModule, ReactiveFormsModule],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: UserService, useClass: MockUserService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenImportComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update fileName and file on file selection", () => {
    const file = new File(["dummy content"], "test.csv", { type: "text/csv" });
    const event = { target: { files: [file] } } as any;
    component.onFileSelected(event);
    expect(component.fileName()).toBe("test.csv");
    expect(component.file.value).toBe(file);
  });

  it("should clear file selection", () => {
    component.file.setValue("dummy");
    component.fileName.set("dummy.csv");
    component.clearFileSelection();
    expect(component.file.value).toBe("");
    expect(component.fileName()).toBe("");
  });

  it("should call importTokens and show notification on success", () => {
    component.file.setValue(new Blob(["data"]));
    component.fileName.set("import.csv");
    component.inputForm.markAsDirty();
    component.inputForm.markAsTouched();
    jest.spyOn(tokenService, "importTokens").mockReturnValue(
      of({
        result: { value: { n_imported: 2, n_not_imported: 1 } }
      } as any)
    );
    component.importTokens();
    expect(tokenService.importTokens).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalledWith("2/3 tokens imported successfully.");
  });

  it("should not call importTokens if form is invalid", () => {
    component.file.setValue("");
    component.fileName.set("");
    component.inputForm.markAsDirty();
    component.inputForm.markAsTouched();
    const spy = jest.spyOn(tokenService, "importTokens");
    component.importTokens();
    expect(spy).not.toHaveBeenCalled();
  });

  it("should validate preSharedKey length for PSKC", () => {
    component.fileType.set("pskc");
    component.preSharedKey.setValue("12345678901234567890123456789012");
    expect(component.preSharedKey.valid).toBe(true);
    component.preSharedKey.setValue("short");
    expect(component.preSharedKey.valid).toBe(false);
  });

  it("should update selectedRealms", () => {
    component.selectedRealms.set(["realm1", "realm2"]);
    expect(component.selectedRealms()).toEqual(["realm1", "realm2"]);
  });

  it("should set PSKC password and validation options", () => {
    component.fileType.set("pskc");
    component.pskPassword.set("mypassword");
    component.pskValidation.set("no_check");
    expect(component.pskPassword()).toBe("mypassword");
    expect(component.pskValidation()).toBe("no_check");
  });

  it("should call importTokens with correct parameters for PSKC file", () => {
    const file = new File(["pskc content"], "pskcfile.pskc", { type: "application/xml" });
    component.fileType.set("pskc");
    component.file.setValue(file);
    component.fileName.set("pskcfile.pskc");
    component.preSharedKey.setValue("12345678901234567890123456789012");
    component.pskPassword.set("testpassword");
    component.pskValidation.set("check_fail_soft");
    component.selectedRealms.set(["realm1", "realm2"]);
    component.inputForm.markAsDirty();
    component.inputForm.markAsTouched();

    const importTokensSpy = jest.spyOn(tokenService, "importTokens").mockReturnValue(
      of({
        result: { value: { n_imported: 1, n_not_imported: 0 } }
      } as any)
    );

    component.importTokens();

    expect(importTokensSpy).toHaveBeenCalledWith("pskcfile.pskc", expect.any(FormData));

    const formDataArg = importTokensSpy.mock.calls[0][1] as FormData;
    expect(formDataArg.get("file")).toBe(file);
    expect(formDataArg.get("type")).toBe("pskc");
    expect(formDataArg.get("tokenrealms")).toBe("realm1,realm2");
    expect(formDataArg.get("psk")).toBe("12345678901234567890123456789012");
    expect(formDataArg.get("password")).toBe("testpassword");
    expect(formDataArg.get("pskcValidateMAC")).toBe("check_fail_soft");
  });

  it("should not include psk and password parameters if they are empty for PSKC file", () => {
    const file = new File(["pskc content"], "pskcfile.pskc", { type: "application/xml" });
    component.fileType.set("pskc");
    component.file.setValue(file);
    component.fileName.set("pskcfile.pskc");
    component.preSharedKey.setValue(""); // empty
    component.pskPassword.set(""); // empty
    component.pskValidation.set("check_fail_hard");
    component.selectedRealms.set(["realm1"]);
    component.inputForm.markAsDirty();
    component.inputForm.markAsTouched();

    const importTokensSpy = jest.spyOn(tokenService, "importTokens").mockReturnValue(
      of({
        result: { value: { n_imported: 1, n_not_imported: 0 } }
      } as any)
    );

    component.importTokens();

    const formDataArg = importTokensSpy.mock.calls[0][1] as FormData;
    expect(formDataArg.get("file")).toBe(file);
    expect(formDataArg.get("type")).toBe("pskc");
    expect(formDataArg.get("tokenrealms")).toBe("realm1");
    expect(formDataArg.get("pskcValidateMAC")).toBe("check_fail_hard");
    expect(formDataArg.has("psk")).toBe(false);
    expect(formDataArg.has("password")).toBe(false);
  });

  it("should register hasChanges based on relevant signals in ngOnInit", () => {
    expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;

    expect(fn()).toBe(false);

    component.fileName.set("token.csv");
    expect(fn()).toBe(true);
    component.fileName.set("");

    component.pskPassword.set("secret");
    expect(fn()).toBe(true);
    component.pskPassword.set("");

    component.fileType.set("pskc");
    expect(fn()).toBe(true);
    component.fileType.set("OATH CSV");

    component.pskValidation.set("check_fail_soft");
    expect(fn()).toBe(true);
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });
});
