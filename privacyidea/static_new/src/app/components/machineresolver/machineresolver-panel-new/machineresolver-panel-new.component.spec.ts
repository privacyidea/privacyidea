import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MachineresolverPanelNewComponent } from "./machineresolver-panel-new.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import {
  Machineresolver,
  MachineresolverData,
  MachineresolverService,
} from "../../../services/machineresolver/machineresolver.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { MockMachineresolverService } from "../../../testing/mock-services/mock-machineresolver-service";

describe("MachineresolverPanelNewComponent", () => {
  let component: MachineresolverPanelNewComponent;
  let fixture: ComponentFixture<MachineresolverPanelNewComponent>;
  let machineresolverService: MockMachineresolverService;
  let dialogService: jasmine.SpyObj<DialogService>;

  beforeEach(async () => {
    const dialogServiceSpy = jasmine.createSpyObj("DialogService", ["confirm"]);

    await TestBed.configureTestingModule({
      imports: [MachineresolverPanelNewComponent, NoopAnimationsModule],
      providers: [
        { provide: MachineresolverService, useClass: MockMachineresolverService },
        { provide: DialogService, useValue: dialogServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MachineresolverPanelNewComponent);
    component = fixture.componentInstance;
    machineresolverService = TestBed.inject(MachineresolverService) as unknown as MockMachineresolverService;
    dialogService = TestBed.inject(DialogService) as jasmine.SpyObj<DialogService>;
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
    const newData: MachineresolverData = { type: "hosts", filename: "newfile" };
    component.onUpdateResolverData(newData);
    expect(component.newMachineresolver().data).toEqual(newData);
  });

  it("should save machineresolver", async () => {
    const panel = { close: () => {} } as any;
    spyOn(panel, "close");
    spyOn(machineresolverService, "postTestMachineresolver").and.returnValue(Promise.resolve(null));
    spyOn(machineresolverService, "postMachineresolver").and.returnValue(Promise.resolve(null));
    await component.saveMachineresolver(panel);
    expect(machineresolverService.postTestMachineresolver).toHaveBeenCalled();
    expect(machineresolverService.postMachineresolver).toHaveBeenCalled();
    expect(panel.close).toHaveBeenCalled();
  });

  it("should handle collapse", () => {
    const panel = { close: () => {}, open: () => {} } as any;
    spyOn(panel, "close");
    spyOn(panel, "open");
    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: "test" });
    dialogService.confirm.and.returnValue(Promise.resolve(true));
    component.handleCollapse(panel);
    expect(dialogService.confirm).toHaveBeenCalled();
  });

  it("should check if machineresolver can be saved", () => {
    component.dataValidatorSignal.set(() => true);
    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: " " });
    expect(component.canSaveMachineresolver()).toBeFalse();

    component.newMachineresolver.set({ ...component.newMachineresolver(), resolvername: "test" });
    expect(component.canSaveMachineresolver()).toBeTrue();

    component.dataValidatorSignal.set(() => false);
    expect(component.canSaveMachineresolver()).toBeFalse();
  });

  it("should reset machineresolver", () => {
    component.newMachineresolver.set({
      resolvername: "test",
      type: "ldap",
      data: { type: "ldap", LDAPURI: "ldap://test" },
    });
    component.resetMachineresolver();
    expect(component.newMachineresolver()).toEqual(component.machineresolverDetault);
  });
});
