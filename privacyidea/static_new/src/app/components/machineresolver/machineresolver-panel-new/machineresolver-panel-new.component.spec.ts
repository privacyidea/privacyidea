import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MachineresolverPanelNewComponent } from "./machineresolver-panel-new.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import {
  HostsMachineresolverData,
  LdapMachineresolverData,
  MachineresolverService
} from "../../../services/machineresolver/machineresolver.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../testing/mock-services/mock-dialog-service";
import { MockMachineresolverService } from "../../../../testing/mock-services/mock-machineresolver-service";

describe("MachineresolverPanelNewComponent", () => {
  let component: MachineresolverPanelNewComponent;
  let fixture: ComponentFixture<MachineresolverPanelNewComponent>;
  let machineresolverServiceMock: MockMachineresolverService;
  let dialogServiceMock: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineresolverPanelNewComponent, NoopAnimationsModule],
      providers: [
        { provide: MachineresolverService, useClass: MockMachineresolverService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(MachineresolverPanelNewComponent);
    component = fixture.componentInstance;
    machineresolverServiceMock = TestBed.inject(MachineresolverService) as unknown as MockMachineresolverService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should change machineresolver type", () => {
    component.onMachineresolverTypeChange("ldap");
    expect(component.newMachineresolver().type).toBe("ldap");
    expect(component.newMachineresolver().data.type).toBe("ldap");
  });

  it("should change resolvername", () => {
    component.onResolvernameChange("newName");
    expect(component.newMachineresolver().resolvername).toBe("newName");
    expect(component.newMachineresolver().data.resolver).toBe("newName");
  });

  it("should update resolver data", () => {
    const newData: HostsMachineresolverData = {
      type: "hosts",
      filename: "newfile",
      resolver: "name"
    };
    component.onUpdateResolverData(newData);
    expect(component.newMachineresolver().data).toEqual(newData);
  });

  it("should save machineresolver", async () => {
    const panel = { close: () => {} } as any;
    jest.spyOn(panel, "close");
    machineresolverServiceMock.postMachineresolver.mockReturnValue(Promise.resolve(null));
    await component.saveMachineresolver(panel);
    expect(machineresolverServiceMock.postTestMachineresolver).toHaveBeenCalled();
    expect(machineresolverServiceMock.postMachineresolver).toHaveBeenCalled();
    expect(panel.close).toHaveBeenCalled();
  });

  it("should handle collapse", () => {
    const panel = { close: () => {}, open: () => {} } as any;
    jest.spyOn(panel, "close");
    jest.spyOn(panel, "open");
    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: "test" });
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(true));
    component.handleCollapse(panel);
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
  });

  it("should check if machineresolver can be saved", () => {
    component.dataValidatorSignal.set(() => true);
    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: " " });
    expect(component.canSaveMachineresolver()).toBeFalsy();

    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: "test" });
    expect(component.canSaveMachineresolver()).toBeTruthy();

    component.dataValidatorSignal.set(() => false);
    expect(component.canSaveMachineresolver()).toBeFalsy();
  });

  it("should reset machineresolver", () => {
    const data: LdapMachineresolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      LDAPBASE: "",
      BINDDN: "",
      BINDPW: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: false,
      resolver: ""
    };
    component.newMachineresolver.set({
      resolvername: "test",
      type: "ldap",
      data: data
    });
    component.resetMachineresolver();
    expect(component.newMachineresolver()).toEqual(component.machineresolverDefault);
  });
});
