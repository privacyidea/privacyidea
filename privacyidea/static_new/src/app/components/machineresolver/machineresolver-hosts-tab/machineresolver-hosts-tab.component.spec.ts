import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MachineresolverHostsTabComponent } from "./machineresolver-hosts-tab.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { HostsMachineresolverData } from "../../../services/machineresolver/machineresolver.service";

describe("MachineresolverHostsTabComponent", () => {
  let component: MachineresolverHostsTabComponent;
  let fixture: ComponentFixture<MachineresolverHostsTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineresolverHostsTabComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineresolverHostsTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("isEditMode", false);
    fixture.componentRef.setInput("machineresolverData", { type: "hosts", filename: "testFileName", resolver: "test" });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit validator on init", () => {
    jest.spyOn(component.onNewValidator, "emit");
    component.ngOnInit();
    expect(component.onNewValidator.emit).toHaveBeenCalled();
  });

  it("should check validity", () => {
    const validData: HostsMachineresolverData = {
      type: "hosts",
      filename: "testFileName",
      resolver: "test"
    };
    const invalidData1 = { type: "ldap" };
    const invalidData2: HostsMachineresolverData = {
      type: "hosts",
      filename: " ",
      resolver: ""
    };
    expect(component.isValid(validData)).toBeTruthy();
    expect(component.isValid(invalidData1 as any)).toBeFalsy();
    expect(component.isValid(invalidData2)).toBeFalsy();
  });

  it("should update data with patch only", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: HostsMachineresolverData = {
      type: "hosts",
      filename: "initial",
      resolver: ""
    };
    fixture.componentRef.setInput("machineresolverData", initialData);
    const patch = { filename: "updated" };
    component.updateData(patch);
    expect(component.onNewData.emit).toHaveBeenCalledWith({ ...initialData, ...patch, type: "hosts" });
  });

  it("should update data with patch and remove", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: HostsMachineresolverData = {
      type: "hosts",
      filename: "initial",
      resolver: "resolver"
    };
    fixture.componentRef.setInput("machineresolverData", initialData);
    const patch = { filename: "updated" };
    component.updateData({ patch, remove: ["resolver"] });
    const expectedData: Partial<HostsMachineresolverData> = { type: "hosts", filename: "updated" };
    expect(component.onNewData.emit).toHaveBeenCalledWith(expectedData);
  });

  it("should update data with remove only", () => {
    jest.spyOn(component.onNewData, "emit");
    const initialData: HostsMachineresolverData = { type: "hosts", filename: "initial", resolver: "name" };
    fixture.componentRef.setInput("machineresolverData", initialData);
    component.updateData({ remove: ["resolver"] });
    const expectedData: Partial<HostsMachineresolverData> = { type: "hosts", filename: "initial" };
    expect(component.onNewData.emit).toHaveBeenCalledWith(expectedData);
  });
});
