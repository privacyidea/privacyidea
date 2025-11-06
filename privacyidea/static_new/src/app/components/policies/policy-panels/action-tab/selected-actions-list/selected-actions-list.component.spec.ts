
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { SelectedActionsListComponent } from "./selected-actions-list.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { signal, input } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("SelectedActionsListComponent", () => {
  let component: SelectedActionsListComponent;
  let fixture: ComponentFixture<SelectedActionsListComponent>;
  let policyServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      isEditMode: signal(false),
      selectedAction: signal(null),
      getDetailsOfAction: jasmine.createSpy("getDetailsOfAction").and.returnValue({ type: "string" }),
      updateActionValue: jasmine.createSpy("updateActionValue"),
    };

    await TestBed.configureTestingModule({
      imports: [SelectedActionsListComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(SelectedActionsListComponent);
    component = fixture.componentInstance;
    component.actions = input([]);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of actions", () => {
    const actions = [{ name: "action1", value: "value1" }, { name: "action2", value: "value2" }];
    component.actions = input(actions);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll(".action-item");
    expect(actionElements.length).toBe(actions.length);
  });

  it("should select an action on click", () => {
    const actions = [{ name: "action1", value: "value1" }];
    component.actions = input(actions);
    fixture.detectChanges();

    const actionElement = fixture.nativeElement.querySelector(".action-item");
    actionElement.click();

    expect(policyServiceMock.selectedAction.set).toHaveBeenCalledWith(actions[0]);
  });

  it("should update boolean action on toggle change", () => {
    const actions = [{ name: "boolAction", value: "true" }];
    component.actions = input(actions);
    policyServiceMock.getDetailsOfAction.and.returnValue({ type: "bool" });
    fixture.detectChanges();

    const toggle = fixture.nativeElement.querySelector("mat-slide-toggle");
    toggle.dispatchEvent(new Event("change"));

    expect(policyServiceMock.updateActionValue).toHaveBeenCalled();
  });
});
