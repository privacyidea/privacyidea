import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { of } from "rxjs";

import { TokenDetailsComponent } from "./token-details.component";
import { TokenService } from "../../../services/token/token.service";
import { ContainerService } from "../../../services/container/container.service";
import { ValidateService } from "../../../services/validate/validate.service";
import { RealmService } from "../../../services/realm/realm.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { OverflowService } from "../../../services/overflow/overflow.service";
import { AuthService } from "../../../services/auth/auth.service";
import { ContentService } from "../../../services/content/content.service";
import { MachineService } from "../../../services/machine/machine.service";
import {
  MockAuthService,
  MockContainerService,
  MockContentService, MockLocalService,
  MockMachineService, MockNotificationService,
  MockOverflowService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService,
  MockValidateService
} from "../../../../testing/mock-services";
import { MatDialog } from "@angular/material/dialog";

describe("TokenDetailsComponent", () => {
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let component: TokenDetailsComponent;

  let tokenSvc: MockTokenService;
  let containerSvc: MockContainerService;
  let realmSvc: MockRealmService;
  let contentSvc: MockContentService;
  let machineSvc: MockMachineService;

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
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: OverflowService, useClass: MockOverflowService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MachineService, useClass: MockMachineService },
        { provide: MatDialog, useValue: matDialogMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    containerSvc = TestBed.inject(ContainerService) as unknown as MockContainerService;
    realmSvc = TestBed.inject(RealmService) as unknown as MockRealmService;
    contentSvc = TestBed.inject(ContentService) as unknown as MockContentService;
    machineSvc = TestBed.inject(MachineService) as unknown as MockMachineService;

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
    const header = fixture.nativeElement.querySelector(".details-header h3:nth-child(2)");
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
    containerSvc.selectedContainer.set("container1");
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.saveContainer();

    expect(containerSvc.assignContainer).toHaveBeenCalledWith("Mock serial", "container1");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("saveContainer does nothing when no container selected", () => {
    containerSvc.selectedContainer.set("");
    (containerSvc.assignContainer as jest.Mock).mockClear();

    component.saveContainer();

    expect(containerSvc.assignContainer).not.toHaveBeenCalled();
  });

  it("deleteContainer unassigns and reloads when selected", () => {
    containerSvc.selectedContainer.set("container1");
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component.deleteContainer();

    expect(containerSvc.unassignContainer).toHaveBeenCalledWith("Mock serial", "container1");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteContainer does nothing when no container selected", () => {
    containerSvc.selectedContainer.set("");
    (containerSvc.unassignContainer as jest.Mock).mockClear();

    component.deleteContainer();

    expect(containerSvc.unassignContainer).not.toHaveBeenCalled();
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

    expect((tokenSvc.getTokengroups as any)).toHaveBeenCalled();
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

    expect((tokenSvc.setTokengroup as any)).toHaveBeenCalledWith("Mock serial", ["groupB"]);
    expect(reloadSpy).toHaveBeenCalled();
    expect(el.isEditing()).toBe(false);
  });

  it("cancelTokenEdit('container_serial') clears selection and toggles editing", () => {
    const el = {
      keyMap: { key: "container_serial" },
      isEditing: signal(true)
    } as any;

    containerSvc.selectedContainer.set("X");
    component.cancelTokenEdit(el);

    expect(containerSvc.selectedContainer()).toBe("");
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

  it("containerSelected marks programmatic change and forwards to ContentService", () => {
    const spy = jest.spyOn(contentSvc, "containerSelected");
    component.containerSelected("C-9");
    expect(component.isProgrammaticTabChange()).toBe(true);
    expect(spy).toHaveBeenCalledWith("C-9");
  });

  it("openSshMachineAssignDialog opens the dialog with expected data", () => {
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
});