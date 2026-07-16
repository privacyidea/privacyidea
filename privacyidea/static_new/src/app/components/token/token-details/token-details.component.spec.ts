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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { of, throwError } from "rxjs";

import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService, AuthResponse } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { MachineService, TokenApplication } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService, TokenTypeKey, TokenInfo, TokenDetails, Tokens } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockPendingChangesService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService,
  MockValidateService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { TokenDetailsComponent } from "./token-details.component";

describe("TokenDetailsComponent", () => {
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let component: TokenDetailsComponent;

  let tokenSvc: MockTokenService;
  let machineSvc: MockMachineService;
  let validateSvc: MockValidateService;
  let router: { navigateByUrl: jest.Mock };

  const matDialogOpen = jest.fn();
  const matDialogMock = { open: matDialogOpen };

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    router = { navigateByUrl: jest.fn().mockResolvedValue(true) };

    // Default: any dialog opened resolves with a truthy result (so "confirm" branches run).
    matDialogOpen.mockReturnValue({ afterClosed: () => of(of({})) });

    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: AuditService, useClass: MockAuditService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: UserService, useClass: MockUserService },
        { provide: MatDialog, useValue: matDialogMock },
        { provide: Router, useValue: router },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    machineSvc = TestBed.inject(MachineService) as unknown as MockMachineService;
    validateSvc = TestBed.inject(ValidateService) as unknown as MockValidateService;

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.tokenIsActive = signal(false);
    component.tokenIsRevoked = signal(false);
    component.infoData = signal([
      { keyMap: { key: "info", label: "Info" }, value: { key1: "value1" }, isEditing: signal(false) }
    ]);
    component.tokenDetailData = signal([
      { keyMap: { key: "container_serial", label: "Container" }, value: "container1", isEditing: signal(false) }
    ]);

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("renders the token serial in the header", () => {
    const header = fixture.nativeElement.querySelector(".details-header .serial");
    expect(header.textContent).toContain("Mock serial");
  });

  it("renders the description editor as a textarea with 3 rows", () => {
    component.tokenDetailData.set([
      {
        keyMap: { key: "description", label: "Description", group: "assignment" },
        value: "some description",
        isEditing: signal(true)
      }
    ]);
    fixture.detectChanges();

    const textarea = fixture.nativeElement.querySelector(".details-card--description textarea");
    expect(textarea).toBeTruthy();
    expect(textarea.getAttribute("rows")).toBe("3");
  });

  it("resetFailCount calls service and reloads", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();
    component.resetFailCount();
    expect(tokenSvc.resetFailCount).toHaveBeenCalledWith("Mock serial");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("saveTokenEdit('description') calls saveTokenDetail and toggles editing off", () => {
    const el: EditableElement = {
      keyMap: { key: "description" },
      value: "newdesc",
      isEditing: signal(true)
    };

    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveTokenEdit(el);

    expect(tokenSvc.saveTokenDetail).toHaveBeenCalledWith("Mock serial", "description", "newdesc");
    expect(reloadSpy).toHaveBeenCalled();
    expect(el.isEditing()).toBe(false);
  });

  it("isEditableElement defers to policy: true/false", () => {
    const spy = jest.spyOn(component["authService"], "actionAllowed");
    spy.mockReturnValueOnce(true);
    expect(component.isEditableElement("description")).toBe(true);

    spy.mockReturnValueOnce(false);
    expect(component.isEditableElement("description")).toBe(false);
  });

  it("openSshMachineAssignDialog opens the dialog with expected data", () => {
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();
    matDialogOpen.mockReturnValue({
      afterClosed: () => of(of({}))
    });
    matDialogOpen.mockClear();
    component.openSshMachineAssignDialog();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
    const call = matDialogOpen.mock.calls[0];
    expect(call[1].data.tokenSerial).toBe("Mock serial");
    expect(call[1].data.tokenType).toBe(component.tokenType());
  });

  it("isAnyEditingOrRevoked reflects editing flags and revoked state", () => {
    // all false
    expect(component.isAnyEditingOrRevoked()).toBe(false);

    // mark an element editing
    const detail = component.tokenDetailData()[0];
    detail.isEditing.set(true);
    expect(component.isAnyEditingOrRevoked()).toBe(true);

    // reset, set revoked
    detail.isEditing.set(false);
    component.tokenIsRevoked.set(true);
    expect(component.isAnyEditingOrRevoked()).toBe(true);

    // reset all
    component.tokenIsRevoked.set(false);
    expect(component.isAnyEditingOrRevoked()).toBe(false);
  });

  it("isAttachedToMachine is true when applications exist", () => {
    machineSvc.tokenApplications.set([]);
    expect(component.isAttachedToMachine()).toBe(false);

    machineSvc.tokenApplications.set([{ id: 1 } as TokenApplication]);
    expect(component.isAttachedToMachine()).toBe(true);
  });

  it("toggleActive calls service and reloads the resource", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();
    component.tokenIsActive.set(true);

    component.toggleActive();

    expect(tokenSvc.toggleActive).toHaveBeenCalledWith("Mock serial", true);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteToken confirms, deletes and navigates to TOKENS route", () => {
    component.deleteToken();

    expect(matDialogOpen).toHaveBeenCalledTimes(1);
    expect(tokenSvc.deleteToken).toHaveBeenCalledWith("Mock serial");
    expect(router.navigateByUrl).toHaveBeenCalled();
    expect(component.tokenSerial()).toBe("");
  });

  it("deleteToken does nothing when dialog is dismissed", () => {
    matDialogOpen.mockReturnValueOnce({ afterClosed: () => of(null) });
    (tokenSvc.deleteToken as jest.Mock).mockClear();

    component.deleteToken();

    expect(tokenSvc.deleteToken).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("revokeToken revokes, refetches details, and reloads", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.revokeToken();

    expect(tokenSvc.revokeToken).toHaveBeenCalledWith("Mock serial");
    expect(tokenSvc.getTokenDetails).toHaveBeenCalledWith("Mock serial");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("revokeToken does nothing when dialog is dismissed", () => {
    matDialogOpen.mockReturnValueOnce({ afterClosed: () => of(null) });
    (tokenSvc.revokeToken as jest.Mock).mockClear();

    component.revokeToken();

    expect(tokenSvc.revokeToken).not.toHaveBeenCalled();
  });

  it("attachSshToMachineDialog opens dialog and reloads applications on close", async () => {
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.attachSshToMachineDialog();
    await Promise.resolve();
    await Promise.resolve();

    expect(matDialogOpen).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("attachHotpToMachineDialog opens dialog and reloads applications on close", async () => {
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.attachHotpToMachineDialog();
    await Promise.resolve();
    await Promise.resolve();

    expect(matDialogOpen).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("attachHotpToMachineDialog does not reload when dialog returns falsy", () => {
    matDialogOpen.mockReturnValueOnce({ afterClosed: () => of(null) });
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.attachHotpToMachineDialog();

    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("attachPasskeyToMachine posts assignment and reloads", () => {
    const postSpy = jest.spyOn(machineSvc, "postAssignMachineToToken");
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.attachPasskeyToMachine();

    expect(postSpy).toHaveBeenCalledWith({
      serial: "Mock serial",
      application: "offline",
      machineid: 0,
      resolver: ""
    });
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("removePasskeyFromMachine deletes assignment and reloads", () => {
    machineSvc.tokenApplications.set([{ id: 77 } as TokenApplication]);
    const delSpy = jest.spyOn(machineSvc, "deleteAssignMachineToToken");
    const reloadSpy = machineSvc.tokenApplicationResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.removePasskeyFromMachine();

    expect(delSpy).toHaveBeenCalledWith({
      serial: "Mock serial",
      application: "offline",
      mtid: "77"
    });
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("openLostTokenDialog opens the LostToken dialog", () => {
    matDialogOpen.mockClear();
    component.openLostTokenDialog();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
  });

  it("rolloverToken opens the rollover dialog when a token is present", () => {
    matDialogOpen.mockClear();
    component.rolloverToken();
    expect(matDialogOpen).toHaveBeenCalledTimes(1);
  });

  it("rolloverToken is a no-op when tokenDetails is falsy", () => {
    matDialogOpen.mockClear();
    component.tokenDetails.set(undefined as unknown as TokenDetails);
    component.rolloverToken();
    expect(matDialogOpen).not.toHaveBeenCalled();
  });

  it("rolloverTokenTypes contains the expected token types", () => {
    const types = component["rolloverTokenTypes"]() as string[];
    expect(types).toContain("totp");
    expect(types).toContain("hotp");
  });

  it("tokenTypeKey reflects the current tokenType signal", () => {
    component.tokenType.set("yubikey");
    expect(component["tokenTypeKey"]()).toBe("yubikey" as TokenTypeKey);
    component.tokenType.set("daypassword");
    expect(component["tokenTypeKey"]()).toBe("daypassword" as TokenTypeKey);
  });

  describe("testPasskey", () => {
    it("reports success when the credential_id hash matches the current token", async () => {
      const credentialId = "AAA"; // any base64url string
      const expectedHash = await sha256HexFromBase64Url(credentialId);
      component.tokenDetails.set({
        ...component.tokenDetails(),
        info: { credential_id_hash: expectedHash } as TokenInfo
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
        args?.onCredentialId?.(credentialId);
        return of({
          result: { value: true, status: true },
          detail: { username: "alice", serial: "Mock serial" }
        } as unknown as AuthResponse);
      });

      component.testPasskey();
      await flushAsync();

      const result = component.passkeyTestResult();
      expect(result?.kind).toBe("success");
      expect(result?.message).toMatch(/alice/);
    });

    it("reports a mismatch with matched serial/user/realm when the hash differs", async () => {
      component.tokenDetails.set({
        ...component.tokenDetails(),
        info: { credential_id_hash: "deadbeef-not-a-real-hash" } as TokenInfo
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
        args?.onCredentialId?.("AAA");
        return of({
          result: { value: true, status: true },
          detail: { username: "bob", serial: "OTHER-SERIAL" }
        } as unknown as AuthResponse);
      });
      (tokenSvc.getTokenDetails as jest.Mock).mockReturnValueOnce(
        of({ result: { value: { tokens: [{ user_realm: "themis" }] } } } as unknown as PiResponse<Tokens>)
      );

      component.testPasskey();
      await flushAsync();

      const result = component.passkeyTestResult();
      expect(result?.kind).toBe("warning");
      expect(result?.message).toMatch(/different passkey/);
      expect(result?.mismatch?.serial).toBe("OTHER-SERIAL");
      expect(result?.mismatch?.username).toBe("bob");
      expect(result?.mismatch?.realm).toBe("themis");
    });

    it("skips mismatch detection for self-service users (non-admin)", async () => {
      const authSvc = TestBed.inject(AuthService) as unknown as MockAuthService;
      authSvc.role.set("user");

      component.tokenDetails.set({
        ...component.tokenDetails(),
        info: { credential_id_hash: "deadbeef-not-a-real-hash" } as TokenInfo
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args) => {
        args?.onCredentialId?.("AAA");
        return of({
          result: { value: true, status: true },
          detail: { username: "carol", serial: "OTHER-SERIAL" }
        } as unknown as AuthResponse);
      });
      const getDetailsSpy = tokenSvc.getTokenDetails as jest.Mock;
      getDetailsSpy.mockClear();

      component.testPasskey();
      await flushAsync();

      const result = component.passkeyTestResult();
      expect(result?.kind).toBe("success");
      expect(result?.mismatch).toBeUndefined();
      expect(getDetailsSpy).not.toHaveBeenCalled();
    });

    it("reports 'No user found' when the validate response is falsy", async () => {
      jest
        .spyOn(validateSvc, "authenticatePasskey")
        .mockReturnValue(of({ result: { value: false, status: true }, detail: {} } as unknown as AuthResponse));

      component.testPasskey();
      await flushAsync();

      const result = component.passkeyTestResult();
      expect(result?.kind).toBe("warning");
      expect(result?.message).toMatch(/No user found/);
    });
  });

  it("attachPasskeyToMachine logs an error when the request fails", () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    jest
      .spyOn(machineSvc, "postAssignMachineToToken")
      .mockReturnValueOnce(throwError(() => new Error("boom")));

    component.attachPasskeyToMachine();

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("removePasskeyFromMachine logs an error when the request fails", () => {
    machineSvc.tokenApplications.set([{ id: 5 } as TokenApplication]);
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    jest
      .spyOn(machineSvc, "deleteAssignMachineToToken")
      .mockReturnValueOnce(throwError(() => new Error("boom")));

    component.removePasskeyFromMachine();

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("cancelTokenEdit on a generic key reloads the resource", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.cancelTokenEdit({
      keyMap: { key: "description" },
      value: "",
      isEditing: signal(true)
    } as EditableElement);

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("showTokenAuditLog sets the audit filter with the token serial", () => {
    const auditSvc = TestBed.inject(AuditService) as unknown as MockAuditService;
    component["showTokenAuditLog"]();
    expect(auditSvc.auditFilter().value).toBe("serial: Mock serial");
  });

  it("saveAllInlineEdits saves editing rows and open user/info edits", async () => {
    const row = component.tokenDetailData()[0];
    row.isEditing.set(true);
    const saveTokenEditSpy = jest.spyOn(component, "saveTokenEdit").mockReturnValue(undefined);

    component.userChild = { saveUser: jest.fn() } as unknown as TokenDetailsComponent["userChild"];
    component.isEditingUser.set(true);

    component.infoChild = { saveInfo: jest.fn() } as unknown as TokenDetailsComponent["infoChild"];
    component.isEditingInfo.set(true);

    await expect(component.saveAllInlineEdits()).resolves.toBe(true);

    expect(saveTokenEditSpy).toHaveBeenCalledWith(row);
    expect(component.userChild!.saveUser).toHaveBeenCalled();
    expect(component.infoChild!.saveInfo).toHaveBeenCalledWith(component.infoData()[0]);
  });

  it("saveAllInlineEdits turns off info editing when no info element exists", async () => {
    component.infoData.set([]);
    component.isEditingInfo.set(true);

    await expect(component.saveAllInlineEdits()).resolves.toBe(true);

    expect(component.isEditingInfo()).toBe(false);
  });

  it("sticky header floats while the sentinel is above the scroll container", () => {
    let observerCallback: IntersectionObserverCallback | undefined;
    (global.IntersectionObserver as unknown as jest.Mock).mockImplementation((cb: IntersectionObserverCallback) => {
      observerCallback = cb;
      return { observe: jest.fn(), unobserve: jest.fn(), disconnect: jest.fn() };
    });

    component.ngAfterViewInit();
    expect(observerCallback).toBeDefined();
    const header = component.stickyHeader.nativeElement;
    const observer = {} as IntersectionObserver;
    const entryAt = (top: number, rootTop: number | null): IntersectionObserverEntry[] =>
      [
        { boundingClientRect: { top }, rootBounds: rootTop === null ? null : { top: rootTop } }
      ] as unknown as IntersectionObserverEntry[];

    observerCallback!(entryAt(-10, 0), observer);
    expect(header.classList.contains("is-sticky")).toBe(true);

    observerCallback!(entryAt(10, 0), observer);
    expect(header.classList.contains("is-sticky")).toBe(false);

    observerCallback!(entryAt(-10, null), observer);
    expect(header.classList.contains("is-sticky")).toBe(false);
  });

  describe("fitWidthToTopRow", () => {
    const rect = (top: number, left: number, right: number): DOMRect =>
      ({ top, left, right, bottom: top + 100, width: right - left, height: 100, x: left, y: top }) as DOMRect;

    const cardEl = (r: DOMRect, hasBox = true): HTMLElement => {
      const el = document.createElement("div");
      el.getBoundingClientRect = () => r;
      el.getClientRects = () => (hasBox ? [r] : []) as unknown as DOMRectList;
      return el;
    };

    const makeContainer = (): HTMLElement => {
      const el = document.createElement("div");
      el.style.padding = "16px";
      el.style.borderWidth = "0px";
      el.style.borderStyle = "solid";
      return el;
    };

    it("fixes the container width to the rendered top-row span plus padding", () => {
      const grid = document.createElement("div");
      grid.appendChild(cardEl(rect(0, 0, 400))); // first row
      grid.appendChild(cardEl(rect(0, 416, 1000))); // first row
      // display:contents wrapper (no box of its own) with a first-row child.
      const wrapper = cardEl(rect(0, 0, 0), false);
      wrapper.appendChild(cardEl(rect(0, 1016, 1200)));
      grid.appendChild(wrapper);
      grid.appendChild(cardEl(rect(200, 0, 400))); // second row -> ignored

      const container = makeContainer();
      (component as any).scrollContainer = { nativeElement: container };
      (component as any).detailsGrid = { nativeElement: grid };

      (component as any).fitWidthToTopRow();

      // span = max right (1200) - min left (0) = 1200; + 2 * 16 padding = 1232.
      expect(container.style.width).toBe("1232px");
    });

    it("clears the fixed width when there are no measurable cards", () => {
      const container = makeContainer();
      container.style.width = "500px";
      (component as any).scrollContainer = { nativeElement: container };
      (component as any).detailsGrid = { nativeElement: document.createElement("div") };

      (component as any).fitWidthToTopRow();

      expect(container.style.width).toBe("");
    });

    it("does nothing when the grid reference is missing", () => {
      const container = makeContainer();
      container.style.width = "300px";
      (component as any).scrollContainer = { nativeElement: container };
      (component as any).detailsGrid = undefined;

      expect(() => (component as any).fitWidthToTopRow()).not.toThrow();
      expect(container.style.width).toBe("300px");
    });

    it("scheduleFit runs the fit on the next animation frame", () => {
      const rafSpy = jest
        .spyOn(window, "requestAnimationFrame")
        .mockImplementation((cb: FrameRequestCallback) => {
          cb(0);
          return 1;
        });
      const fitSpy = jest.spyOn(component as any, "fitWidthToTopRow").mockImplementation(() => {});

      (component as any).scheduleFit();

      expect(fitSpy).toHaveBeenCalledTimes(1);
      rafSpy.mockRestore();
      fitSpy.mockRestore();
    });
  });
});

describe("TokenDetailsComponent linkedSignal computations", () => {
  let component: TokenDetailsComponent;

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: AuditService, useClass: MockAuditService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: UserService, useClass: MockUserService },
        { provide: MatDialog, useValue: { open: jest.fn() } },
        { provide: Router, useValue: { navigateByUrl: jest.fn().mockResolvedValue(true) } },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("recomputes empty rows when tokenDetails is cleared", () => {
    component.tokenDetails.set(undefined as unknown as TokenDetails);
    const data = component.tokenDetailData();
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((d) => d.value === "")).toBe(true);

    const info = component.infoData();
    expect(info.length).toBeGreaterThan(0);
    expect(info.every((d) => d.value === "")).toBe(true);

    const user = component.userData();
    expect(user.length).toBeGreaterThan(0);
    expect(user.every((d) => d.value === "")).toBe(true);
  });

  it("formats timestamp info fields from tokenDetails.info", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "2026-01-15T10:00:00Z" } as TokenInfo
    });

    const created = component.tokenDetailData().find((d) => d.keyMap.key === "creation_date");
    expect(created).toBeDefined();
    expect(typeof created!.value).toBe("string");
    expect(created!.value).not.toBe("");
    expect(created!.value).not.toBe("2026-01-15T10:00:00Z");
  });

  it("keeps the raw value when the timestamp string is unparseable", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "not-a-date" } as TokenInfo
    });

    const created = component.tokenDetailData().find((d) => d.keyMap.key === "creation_date");
    expect(created?.value).toBe("not-a-date");
  });

  it("omits timestamp fields entirely when info value is empty string", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "" } as TokenInfo
    });

    const created = component.tokenDetailData().find((d) => d.keyMap.key === "creation_date");
    expect(created).toBeUndefined();
  });
});

// Helper: drain microtasks AND a macrotask (crypto.subtle.digest may settle on next tick).
async function flushAsync(): Promise<void> {
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
  }
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
}

// Mirror of the component's private SHA-256 helper, used only by the matching-hash test.
async function sha256HexFromBase64Url(b64url: string): Promise<string> {
  const pad = b64url
    .padEnd((b64url.length | 3) + 1, "=")
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const binary = atob(pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
