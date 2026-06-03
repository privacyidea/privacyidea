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
import { webcrypto } from "node:crypto";
import { of } from "rxjs";

if (!(globalThis as any).crypto?.subtle) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
}

import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { MachineService } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService, TokenTypeKey } from "@services/token/token.service";
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
  let containerSvc: MockContainerService;
  let realmSvc: MockRealmService;
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
    containerSvc = TestBed.inject(ContainerService) as unknown as MockContainerService;
    realmSvc = TestBed.inject(RealmService) as unknown as MockRealmService;
    machineSvc = TestBed.inject(MachineService) as unknown as MockMachineService;
    validateSvc = TestBed.inject(ValidateService) as unknown as MockValidateService;

    // Monkey-patch unimplemented service methods we’ll hit via the component.
    (tokenSvc.getTokengroups as any) = jest
      .fn()
      .mockReturnValue(of({ result: { status: true, value: { groupA: {}, groupB: {} } } }));
    (tokenSvc.setTokengroup as any) = jest.fn().mockReturnValue(of({}));
    (tokenSvc.setTokenRealm as any) = jest.fn().mockReturnValue(of({}));

    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.tokenIsActive = signal(false);
    component.tokenIsRevoked = signal(false);
    component.tokengroupOptions = signal(["group1", "group2"]);
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

  it("tokenDetailDataByGroup hides the counters group for webauthn, passkey and push", () => {
    component.tokenDetailData.set([
      { keyMap: { key: "maxfail", label: "Max Count", group: "counters" }, value: 10, isEditing: signal(false) },
      { keyMap: { key: "tokentype", label: "Type", group: "identity" }, value: "hotp", isEditing: signal(false) }
    ] as any);

    for (const tokentype of ["webauthn", "passkey", "push"]) {
      component.tokenDetails.set({ ...component.tokenDetails(), tokentype: tokentype as TokenTypeKey });
      expect(component.tokenDetailDataByGroup().some((group) => group.id === "counters")).toBe(false);
    }

    component.tokenDetails.set({ ...component.tokenDetails(), tokentype: "hotp" });
    expect(component.tokenDetailDataByGroup().find((group) => group.id === "counters")?.rows.length).toBe(1);
  });

  it("renders the description editor as a textarea with 7 rows", () => {
    component.tokenDetailData.set([
      {
        keyMap: { key: "description", label: "Description", group: "assignment" },
        value: "some description",
        isEditing: signal(true)
      }
    ] as any);
    fixture.detectChanges();

    const textarea = fixture.nativeElement.querySelector(".description-row textarea");
    expect(textarea).toBeTruthy();
    expect(textarea.getAttribute("rows")).toBe("7");
  });

  it("resetFailCount calls service and reloads", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();
    component.resetFailCount();
    expect(tokenSvc.resetFailCount).toHaveBeenCalledWith("Mock serial");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("saveContainer assigns when a container is selected", () => {
    containerSvc.selectedContainerSerial.set("container1");
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveContainer();

    expect(containerSvc.addToken).toHaveBeenCalledWith("Mock serial", "container1");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("saveContainer does nothing when no container selected", () => {
    containerSvc.selectedContainerSerial.set("");
    (containerSvc.addToken as jest.Mock).mockClear();

    component.saveContainer();

    expect(containerSvc.addToken).not.toHaveBeenCalled();
  });

  it("removeFromContainer removes token and reloads when selected", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      serial: "Mock serial",
      container_serial: "container1"
    });

    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.removeFromContainer();

    expect(containerSvc.removeToken).toHaveBeenCalledWith("Mock serial", "container1");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("removeFromContainer does nothing when no container selected", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      serial: "Mock serial",
      container_serial: ""
    });

    (containerSvc.removeToken as jest.Mock).mockClear();

    component.removeFromContainer();

    expect(containerSvc.removeToken).not.toHaveBeenCalled();
  });

  it("toggleTokenEdit('tokengroup') loads tokengroups once and toggles editing", () => {
    const tgEl = {
      keyMap: { key: "tokengroup", label: "Token Groups" },
      value: [],
      isEditing: signal(false)
    } as any;

    component.tokenDetailData.set([...component.tokenDetailData(), tgEl]);
    component.tokengroupOptions.set([]);
    component.toggleTokenEdit(tgEl);

    expect(tokenSvc.getTokengroups as any).toHaveBeenCalled();
    expect(component.tokengroupOptions()).toEqual(["groupA", "groupB"]);
    expect(tgEl.isEditing()).toBe(true);
  });

  it("saveTokenEdit('description') calls saveTokenDetail and toggles editing off", () => {
    const el = {
      keyMap: { key: "description" },
      value: "newdesc",
      isEditing: signal(true)
    } as any;

    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveTokenEdit(el);

    expect(tokenSvc.saveTokenDetail).toHaveBeenCalledWith("Mock serial", "description", "newdesc");
    expect(reloadSpy).toHaveBeenCalled();
    expect(el.isEditing()).toBe(false);
  });

  it("saveTokenEdit('tokengroup') uses setTokengroup and reloads", () => {
    const el = {
      keyMap: { key: "tokengroup" },
      value: ["groupA"],
      isEditing: signal(true)
    } as any;

    component.selectedTokengroup.set(["groupB"]);
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveTokenEdit(el);

    expect(tokenSvc.setTokengroup as any).toHaveBeenCalledWith("Mock serial", ["groupB"]);
    expect(reloadSpy).toHaveBeenCalled();
    expect(el.isEditing()).toBe(false);
  });

  it("cancelTokenEdit('container_serial') clears selection and toggles editing", () => {
    const el = {
      keyMap: { key: "container_serial" },
      isEditing: signal(true)
    } as any;

    containerSvc.selectedContainerSerial.set("X");
    component.cancelTokenEdit(el);

    expect(containerSvc.selectedContainerSerial()).toBe("");
    expect(el.isEditing()).toBe(false);
  });

  it("isEditableElement defers to policy: true/false", () => {
    const spy = jest.spyOn((component as any).authService, "actionAllowed");
    spy.mockReturnValueOnce(true);
    expect(component.isEditableElement("description")).toBe(true);

    spy.mockReturnValueOnce(false);
    expect(component.isEditableElement("description")).toBe(false);
  });

  it("isNumberElement identifies numeric fields", () => {
    expect(component.isNumberElement("maxfail")).toBe(true);
    expect(component.isNumberElement("count_window")).toBe(true);
    expect(component.isNumberElement("sync_window")).toBe(true);
    expect(component.isNumberElement("description")).toBe(false);
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

    machineSvc.tokenApplications.set([{ id: 1 } as any]);
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
    machineSvc.tokenApplications.set([{ id: 77 } as any]);
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
    component.tokenDetails.set(undefined as any);
    component.rolloverToken();
    expect(matDialogOpen).not.toHaveBeenCalled();
  });

  it("rolloverTokenTypes contains the expected token types", () => {
    const types = (component as any).rolloverTokenTypes() as string[];
    expect(types).toContain("totp");
    expect(types).toContain("hotp");
  });

  it("tokenTypeKey reflects the current tokenType signal", () => {
    component.tokenType.set("yubikey");
    expect((component as any).tokenTypeKey()).toBe("yubikey" as TokenTypeKey);
    component.tokenType.set("daypassword");
    expect((component as any).tokenTypeKey()).toBe("daypassword" as TokenTypeKey);
  });

  describe("testPasskey", () => {
    it("reports success when the credential_id hash matches the current token", async () => {
      const credentialId = "AAA"; // any base64url string
      const expectedHash = await sha256HexFromBase64Url(credentialId);
      component.tokenDetails.set({
        ...component.tokenDetails(),
        info: { credential_id_hash: expectedHash } as any
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args: any) => {
        args?.onCredentialId?.(credentialId);
        return of({
          result: { value: true, status: true } as any,
          detail: { username: "alice", serial: "Mock serial" } as any
        } as any);
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
        info: { credential_id_hash: "deadbeef-not-a-real-hash" } as any
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args: any) => {
        args?.onCredentialId?.("AAA");
        return of({
          result: { value: true, status: true } as any,
          detail: { username: "bob", serial: "OTHER-SERIAL" } as any
        } as any);
      });
      (tokenSvc.getTokenDetails as jest.Mock).mockReturnValueOnce(
        of({ result: { value: { tokens: [{ user_realm: "themis" }] } } } as any)
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
      const authSvc = TestBed.inject(AuthService) as any;
      authSvc.role.set("user");

      component.tokenDetails.set({
        ...component.tokenDetails(),
        info: { credential_id_hash: "deadbeef-not-a-real-hash" } as any
      });

      jest.spyOn(validateSvc, "authenticatePasskey").mockImplementation((args: any) => {
        args?.onCredentialId?.("AAA");
        return of({
          result: { value: true, status: true } as any,
          detail: { username: "carol", serial: "OTHER-SERIAL" } as any
        } as any);
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
        .mockReturnValue(of({ result: { value: false, status: true } as any, detail: {} as any } as any));

      component.testPasskey();
      await flushAsync();

      const result = component.passkeyTestResult();
      expect(result?.kind).toBe("warning");
      expect(result?.message).toMatch(/No user found/);
    });
  });

  it("attachPasskeyToMachine logs an error when the request fails", () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    jest
      .spyOn(machineSvc, "postAssignMachineToToken")
      .mockReturnValueOnce((require("rxjs") as typeof import("rxjs")).throwError(() => new Error("boom")));

    component.attachPasskeyToMachine();

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("removePasskeyFromMachine logs an error when the request fails", () => {
    machineSvc.tokenApplications.set([{ id: 5 } as any]);
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    jest
      .spyOn(machineSvc, "deleteAssignMachineToToken")
      .mockReturnValueOnce((require("rxjs") as typeof import("rxjs")).throwError(() => new Error("boom")));

    component.removePasskeyFromMachine();

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("saveTokenEdit('container_serial') trims selection and calls saveContainer", () => {
    containerSvc.selectedContainerSerial.set("  trimmed  ");
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveTokenEdit({
      keyMap: { key: "container_serial" },
      value: "",
      isEditing: signal(true)
    } as any);

    expect(containerSvc.addToken).toHaveBeenCalledWith("Mock serial", "trimmed");
  });

  it("saveTokenEdit('realms') calls setTokenRealm and reloads", () => {
    realmSvc.selectedRealms.set(["realmA"]);
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveTokenEdit({
      keyMap: { key: "realms" },
      value: [],
      isEditing: signal(true)
    } as any);

    expect(tokenSvc.setTokenRealm as any).toHaveBeenCalledWith("Mock serial", ["realmA"]);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("cancelTokenEdit('tokengroup') restores selection from token detail data", () => {
    component.tokenDetailData.set([
      { keyMap: { key: "tokengroup", label: "Token Groups" }, value: ["g1"], isEditing: signal(true) }
    ] as any);

    component.cancelTokenEdit({
      keyMap: { key: "tokengroup" },
      isEditing: signal(true)
    } as any);

    expect(component.selectedTokengroup()).toEqual(["g1"]);
  });

  it("cancelTokenEdit('realms') restores selection from token detail data", () => {
    component.tokenDetailData.set([
      { keyMap: { key: "realms", label: "Realms" }, value: ["realmZ"], isEditing: signal(true) }
    ] as any);

    component.cancelTokenEdit({
      keyMap: { key: "realms" },
      isEditing: signal(true)
    } as any);

    expect(realmSvc.selectedRealms()).toEqual(["realmZ"]);
  });

  it("cancelTokenEdit on a generic key reloads the resource", () => {
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.cancelTokenEdit({
      keyMap: { key: "description" },
      isEditing: signal(true)
    } as any);

    expect(reloadSpy).toHaveBeenCalled();
  });

  it("showTokenAuditLog sets the audit filter with the token serial", () => {
    const auditSvc = TestBed.inject(AuditService) as any;
    (component as any).showTokenAuditLog();
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
    component.tokenDetails.set(undefined as any);
    const data = component.tokenDetailData();
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((d: any) => d.value === "")).toBe(true);

    const info = component.infoData();
    expect(info.length).toBeGreaterThan(0);
    expect(info.every((d: any) => d.value === "")).toBe(true);

    const user = component.userData();
    expect(user.length).toBeGreaterThan(0);
    expect(user.every((d: any) => d.value === "")).toBe(true);
  });

  it("formats timestamp info fields from tokenDetails.info", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "2026-01-15T10:00:00Z" } as any
    });

    const created = component.tokenDetailData().find((d: any) => d.keyMap.key === "creation_date");
    expect(created).toBeDefined();
    expect(typeof created!.value).toBe("string");
    expect(created!.value).not.toBe("");
    expect(created!.value).not.toBe("2026-01-15T10:00:00Z");
  });

  it("keeps the raw value when the timestamp string is unparseable", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "not-a-date" } as any
    });

    const created = component.tokenDetailData().find((d: any) => d.keyMap.key === "creation_date");
    expect(created?.value).toBe("not-a-date");
  });

  it("omits timestamp fields entirely when info value is empty string", () => {
    component.tokenDetails.set({
      ...component.tokenDetails(),
      info: { creation_date: "" } as any
    });

    const created = component.tokenDetailData().find((d: any) => d.keyMap.key === "creation_date");
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
