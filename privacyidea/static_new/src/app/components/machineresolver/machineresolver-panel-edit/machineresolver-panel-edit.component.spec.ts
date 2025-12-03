import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MachineresolverPanelEditComponent } from "./machineresolver-panel-edit.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import {
  HostsMachineresolver,
  HostsMachineresolverData,
  MachineresolverService
} from "../../../services/machineresolver/machineresolver.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { MockNotificationService } from "../../../../testing/mock-services";
import { MockMachineresolverService } from "../../../../testing/mock-services/mock-machineresolver-service";
import { Component } from "@angular/core";
import { MockDialogService } from "../../../../testing/mock-services/mock-dialog-service";

@Component({
  standalone: true,
  selector: "app-machineresolver-hosts-tab",
  template: ""
})
class MachineresolverHostsTabComponent {}

@Component({
  standalone: true,
  selector: "app-machineresolver-ldap-tab",
  template: ""
})
class MachineresolverLdapTabComponent {}

describe("MachineresolverPanelEditComponent", () => {
  let component: MachineresolverPanelEditComponent;
  let fixture: ComponentFixture<MachineresolverPanelEditComponent>;
  let machineresolverServiceMock: MockMachineresolverService;
  let dialogServiceMock: MockDialogService;
  let notificationServiceMock: MockNotificationService;

  const machineresolver: HostsMachineresolver = {
    resolvername: "test",
    type: "hosts",
    data: {
      resolver: "test",
      type: "hosts",
      filename: "testfile"
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineresolverPanelEditComponent, NoopAnimationsModule],
      providers: [
        { provide: MachineresolverService, useClass: MockMachineresolverService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    })
      .overrideComponent(MachineresolverPanelEditComponent, {
        set: {
          imports: [MachineresolverHostsTabComponent, MachineresolverLdapTabComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(MachineresolverPanelEditComponent);
    component = fixture.componentInstance;
    machineresolverServiceMock = TestBed.inject(MachineresolverService) as unknown as MockMachineresolverService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    fixture.componentRef.setInput("originalMachineresolver", machineresolver);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should enter edit mode", () => {
    expect(component.isEditMode()).toBeFalsy();
    component.isEditMode.set(true);
    expect(component.isEditMode()).toBeTruthy();
  });

  it("should change machineresolver type", () => {
    component.isEditMode.set(true);
    component.onMachineresolverTypeChange("ldap");
    expect(component.editedMachineresolver().type).toBe("ldap");
    expect(component.editedMachineresolver().data.type).toBe("ldap");
  });

  it("should change resolvername", () => {
    component.isEditMode.set(true);
    component.onResolvernameChange("newName");
    expect(component.editedMachineresolver().resolvername).toBe("newName");
    expect(component.editedMachineresolver().data.resolver).toBe("newName");
  });

  it("should update resolver data", () => {
    component.isEditMode.set(true);
    const newData: HostsMachineresolverData = {
      type: "hosts",
      filename: "newfile",
      resolver: "test"
    };
    component.onUpdateResolverData(newData);
    expect(component.editedMachineresolver().data).toEqual(newData);
  });

  it("should save machineresolver successfully", async () => {
    machineresolverServiceMock.postTestMachineresolver.mockReturnValue(Promise.resolve(null));
    machineresolverServiceMock.postMachineresolver.mockReturnValue(Promise.resolve(null));
    component.isEditMode.set(true);
    await component.saveMachineresolver();
    expect(machineresolverServiceMock.postTestMachineresolver).toHaveBeenCalled();
    expect(machineresolverServiceMock.postMachineresolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should save machineresolver despite test failure if confirmed", async () => {
    machineresolverServiceMock.postTestMachineresolver.mockReturnValue(Promise.reject(Error("post-failed")));
    machineresolverServiceMock.postMachineresolver.mockReturnValue(Promise.resolve(null));
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(true));
    component.isEditMode.set(true);
    await component.saveMachineresolver();
    expect(machineresolverServiceMock.postTestMachineresolver).toHaveBeenCalled();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(machineresolverServiceMock.postMachineresolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should not save machineresolver if test fails and not confirmed", async () => {
    machineresolverServiceMock.postTestMachineresolver.mockReturnValue(Promise.reject(Error("post-failed")));
    machineresolverServiceMock.postMachineresolver.mockReturnValue(Promise.resolve(null));
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(false));
    component.isEditMode.set(true);
    await component.saveMachineresolver();
    expect(machineresolverServiceMock.postTestMachineresolver).toHaveBeenCalled();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(machineresolverServiceMock.postMachineresolver).not.toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy(); // Should remain in edit mode
  });

  it("should not save machineresolver if post fails", async () => {
    machineresolverServiceMock.postTestMachineresolver.mockReturnValue(Promise.resolve(null));
    machineresolverServiceMock.postMachineresolver.mockReturnValue(Promise.reject(Error("save-failed")));
    component.isEditMode.set(true);
    await component.saveMachineresolver();
    expect(machineresolverServiceMock.postTestMachineresolver).toHaveBeenCalled();
    expect(machineresolverServiceMock.postMachineresolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy(); // Should remain in edit mode
  });

  it("should delete machineresolver if confirmed", async () => {
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(true));
    machineresolverServiceMock.deleteMachineresolver.mockReturnValue(Promise.resolve(null));
    await component.deleteMachineresolver();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(machineresolverServiceMock.deleteMachineresolver).toHaveBeenCalledWith("test");
  });

  it("should not delete machineresolver if cancelled", async () => {
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(false));
    machineresolverServiceMock.deleteMachineresolver.mockReturnValue(Promise.resolve(null));
    await component.deleteMachineresolver();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(machineresolverServiceMock.deleteMachineresolver).not.toHaveBeenCalled();
  });

  it("should cancel edit mode if not edited", () => {
    component.isEditMode.set(true);
    TestBed.flushEffects();
    component.cancelEditMode();
    expect(component.isEditMode()).toBeFalsy();
    expect(dialogServiceMock.confirm).not.toHaveBeenCalled();
  });

  it("should cancel edit mode if edited and dialog confirmed", async () => {
    component.isEditMode.set(true);
    component.editedMachineresolver.set({ ...machineresolver, type: "ldap" });
    TestBed.flushEffects();
    expect(component.isEdited()).toBeTruthy();
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(true));
    component.cancelEditMode();
    await Promise.resolve();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
    expect(component.editedMachineresolver().type).toBe("hosts");
  });

  it("should not cancel edit mode if edited and dialog cancelled", () => {
    component.isEditMode.set(true);
    component.editedMachineresolver.set({ ...machineresolver, type: "ldap" });
    TestBed.flushEffects();
    expect(component.isEdited()).toBeTruthy();
    dialogServiceMock.confirm.mockReturnValue(Promise.resolve(false));
    component.cancelEditMode();
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy();
    expect(component.editedMachineresolver().type).toBe("ldap");
  });

  describe("check if machineresolver can be saved", () => {
    it("when data and resolvername are valid", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => true);
      component.editedMachineresolver.set({ ...machineresolver, resolvername: "test" });
      expect(component.canSaveMachineresolver()).toBeTruthy();
    });

    it("when data is valid but resolvername is empty", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => true);
      component.editedMachineresolver.set({ ...machineresolver, resolvername: " " }); // Should not be empty (trimmed)
      expect(component.canSaveMachineresolver()).toBeFalsy();
    });

    it("when data is invalid but resolvername is valid", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => false);
      component.editedMachineresolver.set({ ...machineresolver, resolvername: "test" });
      expect(component.canSaveMachineresolver()).toBeFalsy();
    });

    it("when both data and resolvername are invalid", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => false);
      component.editedMachineresolver.set({ ...machineresolver, resolvername: " " }); // Should not be empty (trimmed)
      expect(component.canSaveMachineresolver()).toBeFalsy();
    });
  });
});
