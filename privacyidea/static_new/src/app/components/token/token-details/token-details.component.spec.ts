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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";

import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute } from "@angular/router";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { MachineService } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockMachineService,
  MockNotificationService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService,
  MockValidateService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { TokenDetailsComponent } from "./token-details.component";

describe("TokenDetailsComponent", () => {
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let component: TokenDetailsComponent;

  let tokenSvc: MockTokenService;
  let containerSvc: MockContainerService;
  let realmSvc: MockRealmService;
  let contentSvc: MockContentService;
  let machineSvc: MockMachineService;
  let pendingChangesService: MockPendingChangesService;

  const matDialogOpen = jest.fn();
  const matDialogMock = { open: matDialogOpen };

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
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
        { provide: MatDialog, useValue: matDialogMock },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    containerSvc = TestBed.inject(ContainerService) as unknown as MockContainerService;
    realmSvc = TestBed.inject(RealmService) as unknown as MockRealmService;
    contentSvc = TestBed.inject(ContentService) as unknown as MockContentService;
    machineSvc = TestBed.inject(MachineService) as unknown as MockMachineService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

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
    const header = fixture.nativeElement.querySelector(".details-header .token-serial");
    expect(header.textContent).toContain("Mock serial");
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

  describe("pending changes", () => {
    it("registers hasChanges in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    });

    it("hasChanges reflects editing state of inline fields", () => {
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      expect(fn()).toBe(false);

      component.isEditingUser.set(true);
      expect(fn()).toBe(true);
      component.isEditingUser.set(false);

      component.isEditingInfo.set(true);
      expect(fn()).toBe(true);
    });

    it("hasChanges ignores tokenIsRevoked (only edit state matters)", () => {
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      component.tokenIsRevoked.set(true);
      expect(fn()).toBe(false);
    });

    it("ngOnDestroy clears all pending-changes registrations", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });

    it("registers validChanges and save in ngOnInit", () => {
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("saveAllInlineEdits saves every row with isEditing()=true", async () => {
      const editingRow = {
        keyMap: { key: "description", label: "Description" },
        value: "new",
        isEditing: signal(true)
      } as any;
      const idleRow = {
        keyMap: { key: "maxfail", label: "Max" },
        value: 5,
        isEditing: signal(false)
      } as any;
      (component as any).tokenDetailData = () => [editingRow, idleRow];
      const saveSpy = jest.spyOn(component, "saveTokenEdit").mockImplementation(() => {});

      const result = await component.saveAllInlineEdits();

      expect(result).toBe(true);
      expect(saveSpy).toHaveBeenCalledTimes(1);
      expect(saveSpy).toHaveBeenCalledWith(editingRow);
    });

    it("saveAllInlineEdits delegates user save to userChild when isEditingUser", async () => {
      (component as any).tokenDetailData = () => [];
      component.isEditingUser.set(true);
      const userSaveSpy = jest.fn();
      component.userChild = { saveUser: userSaveSpy } as any;

      await component.saveAllInlineEdits();

      expect(userSaveSpy).toHaveBeenCalled();
    });

    it("saveAllInlineEdits delegates info save to infoChild when isEditingInfo and info exists", async () => {
      (component as any).tokenDetailData = () => [];
      const infoEl = {
        keyMap: { key: "info", label: "Information" },
        value: { foo: "bar" },
        isEditing: signal(true)
      } as any;
      (component as any).infoData = () => [infoEl];
      component.isEditingInfo.set(true);
      const infoSaveSpy = jest.fn();
      component.infoChild = { saveInfo: infoSaveSpy } as any;

      await component.saveAllInlineEdits();

      expect(infoSaveSpy).toHaveBeenCalledWith(infoEl);
    });
  });
});
