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
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenImportResult, TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import { MockNotificationService, MockRealmService, MockTokenService, MockUserService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
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
    }

    (globalThis as unknown as { IntersectionObserver: typeof IO }).IntersectionObserver = IO;
  });

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenImportComponent],
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

  const setModel = (patch: Partial<ReturnType<typeof component.importModel>>) =>
    component.importModel.update((model) => ({ ...model, ...patch }));

  it("should update fileName and file on file selection", () => {
    const file = new File(["dummy content"], "test.csv", { type: "text/csv" });
    const event = { target: { files: [file] } } as unknown as Event;
    component.onFileSelected(event);
    expect(component.fileName()).toBe("test.csv");
    expect(component.file()).toBe(file);
  });

  it("should clear file selection", () => {
    component.file.set("dummy");
    component.fileName.set("dummy.csv");
    component.clearFileSelection();
    expect(component.file()).toBe("");
    expect(component.fileName()).toBe("");
  });

  it("should call importTokens and show notification on success", () => {
    component.file.set(new File(["data"], "import.csv"));
    component.fileName.set("import.csv");
    jest
      .spyOn(tokenService, "importTokens")
      .mockReturnValue(of(MockPiResponse.fromValue<TokenImportResult>({ n_imported: 2, n_not_imported: 1 })));
    component.importTokens();
    expect(tokenService.importTokens).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalledWith("2/3 tokens imported successfully.");
  });

  it("should not call importTokens if form is invalid", () => {
    component.file.set("");
    component.fileName.set("");
    const spy = jest.spyOn(tokenService, "importTokens");
    component.importTokens();
    expect(spy).not.toHaveBeenCalled();
  });

  it("should validate preSharedKey length for PSKC", () => {
    setModel({ fileType: "pskc", preSharedKey: "12345678901234567890123456789012" });
    expect(component.importForm.preSharedKey().valid()).toBe(true);
    setModel({ preSharedKey: "short" });
    expect(component.importForm.preSharedKey().valid()).toBe(false);
    expect(
      component.importForm
        .preSharedKey()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["pskLength"]);
    setModel({ preSharedKey: "" });
    expect(component.importForm.preSharedKey().valid()).toBe(true);
  });

  it("ignores a stale preSharedKey once the file type is not PSKC", () => {
    component.file.set(new File(["data"], "import.csv"));
    setModel({ fileType: "pskc", preSharedKey: "short" });
    expect(component.canImport()).toBe(false);

    setModel({ fileType: "OATH CSV" });

    expect(component.importForm.preSharedKey().disabled()).toBe(true);
    expect(component.canImport()).toBe(true);
  });

  it("enables the import button only with a file and valid fields", () => {
    const button = (): HTMLButtonElement => fixture.nativeElement.querySelector(".sticky-controls button");
    expect(button().disabled).toBe(true);
    component.file.set(new File(["data"], "import.csv"));
    fixture.detectChanges();
    expect(button().disabled).toBe(false);
    setModel({ fileType: "pskc", preSharedKey: "short" });
    fixture.detectChanges();
    expect(button().disabled).toBe(true);
  });

  it("does not import with an invalid preSharedKey", () => {
    component.file.set(new File(["data"], "import.pskc"));
    setModel({ fileType: "pskc", preSharedKey: "short" });
    const spy = jest.spyOn(tokenService, "importTokens");
    component.importTokens();
    expect(spy).not.toHaveBeenCalled();
  });

  it("typing a short key shows the length error once touched", () => {
    setModel({ fileType: "pskc" });
    fixture.detectChanges();
    const el: HTMLInputElement = fixture.nativeElement.querySelector("mat-form-field input[placeholder^='Pre Shared']");
    el.value = "abc";
    el.dispatchEvent(new Event("input"));
    el.dispatchEvent(new Event("blur"));
    fixture.detectChanges();
    expect(component.importModel().preSharedKey).toBe("abc");
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("32 characters long hex string");
  });

  it("typing the PSKC password updates the model", () => {
    setModel({ fileType: "pskc" });
    fixture.detectChanges();
    const el: HTMLInputElement = fixture.nativeElement.querySelector("mat-form-field input[placeholder='Password']");
    el.value = "secret";
    el.dispatchEvent(new Event("input"));
    expect(component.importModel().pskPassword).toBe("secret");
  });

  it("keeps the default realm selected and updates selectedRealms through the field", () => {
    component.importForm.selectedRealms().controlValue.set(["realm1", "realm2"]);
    expect(component.importModel().selectedRealms).toEqual(["realm1", "realm2"]);
  });

  it("should set PSKC password and validation options", () => {
    setModel({ fileType: "pskc", pskPassword: "mypassword", pskValidation: "no_check" });
    expect(component.importForm.pskPassword().value()).toBe("mypassword");
    expect(component.importForm.pskValidation().value()).toBe("no_check");
  });

  it("should call importTokens with correct parameters for PSKC file", () => {
    const file = new File(["pskc content"], "pskcfile.pskc", { type: "application/xml" });
    component.file.set(file);
    component.fileName.set("pskcfile.pskc");
    setModel({
      fileType: "pskc",
      preSharedKey: "12345678901234567890123456789012",
      pskPassword: "testpassword",
      pskValidation: "check_fail_soft",
      selectedRealms: ["realm1", "realm2"]
    });

    const importTokensSpy = jest
      .spyOn(tokenService, "importTokens")
      .mockReturnValue(of(MockPiResponse.fromValue<TokenImportResult>({ n_imported: 1, n_not_imported: 0 })));

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
    component.file.set(file);
    component.fileName.set("pskcfile.pskc");
    setModel({
      fileType: "pskc",
      preSharedKey: "",
      pskPassword: "",
      pskValidation: "check_fail_hard",
      selectedRealms: ["realm1"]
    });

    const importTokensSpy = jest
      .spyOn(tokenService, "importTokens")
      .mockReturnValue(of(MockPiResponse.fromValue<TokenImportResult>({ n_imported: 1, n_not_imported: 0 })));

    component.importTokens();

    const formDataArg = importTokensSpy.mock.calls[0][1] as FormData;
    expect(formDataArg.get("file")).toBe(file);
    expect(formDataArg.get("type")).toBe("pskc");
    expect(formDataArg.get("tokenrealms")).toBe("realm1");
    expect(formDataArg.get("pskcValidateMAC")).toBe("check_fail_hard");
    expect(formDataArg.has("psk")).toBe(false);
    expect(formDataArg.has("password")).toBe(false);
  });

  it("should register hasChanges from the file name and the dirty form", () => {
    expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;

    expect(fn()).toBe(false);

    component.fileName.set("token.csv");
    expect(fn()).toBe(true);
    component.fileName.set("");
    expect(fn()).toBe(false);

    component.importForm.pskPassword().controlValue.set("secret");
    expect(fn()).toBe(true);
  });

  it("does not report changes after a preselected realm is rendered", () => {
    setModel({ selectedRealms: ["realm1"] });
    fixture.detectChanges();
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
    expect(component.importForm().dirty()).toBe(false);
    expect(fn()).toBe(false);
  });

  it("reports changes when the file type changes through the control", () => {
    const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
    component.importForm.fileType().controlValue.set("pskc");
    expect(fn()).toBe(true);
  });

  it("renders the preselected realm in the multi-select without marking the form dirty", async () => {
    const realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    realmService.realmOptions.set(["realm1", "realm2"]);
    setModel({ selectedRealms: ["realm1"] });
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const select = fixture.nativeElement.querySelector("mat-select[multiple]") as HTMLElement;
    expect(select.textContent).toContain("realm1");
    expect(component.importForm().dirty()).toBe(false);
  });

  it("picking realm options in the multi-select updates the model and marks the form dirty", () => {
    const realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    realmService.realmOptions.set(["realm1", "realm2"]);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector("mat-select[multiple] .mat-mdc-select-trigger") as HTMLElement).click();
    fixture.detectChanges();
    const options = Array.from(document.querySelectorAll("mat-option")) as HTMLElement[];
    options.find((o) => o.textContent?.includes("realm2"))?.click();
    fixture.detectChanges();
    expect(component.importModel().selectedRealms).toContain("realm2");
    expect(component.importForm.selectedRealms().dirty()).toBe(true);
  });

  it("choosing the PSKC file type in the select shows the pre shared key field", () => {
    expect(fixture.nativeElement.querySelector("input[placeholder^='Pre Shared']")).toBeNull();
    (fixture.nativeElement.querySelector("mat-select .mat-mdc-select-trigger") as HTMLElement).click();
    fixture.detectChanges();
    const options = Array.from(document.querySelectorAll("mat-option")) as HTMLElement[];
    options.find((o) => o.textContent?.includes("PSKC File"))?.click();
    fixture.detectChanges();
    expect(component.importModel().fileType).toBe("pskc");
    expect(fixture.nativeElement.querySelector("input[placeholder^='Pre Shared']")).not.toBeNull();
  });

  it("ngOnDestroy clears all pending-changes registrations", () => {
    component.ngOnDestroy();
    expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
  });
});
