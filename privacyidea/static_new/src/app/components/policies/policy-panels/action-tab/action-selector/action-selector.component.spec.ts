
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActionSelectorComponent } from "./action-selector.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("ActionSelectorComponent", () => {
  let component: ActionSelectorComponent;
  let fixture: ComponentFixture<ActionSelectorComponent>;
  let policyServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      availableActions: signal([]),
      selectedAction: signal(null),
      selectAction: jasmine.createSpy("selectAction"),
    };

    await TestBed.configureTestingModule({
      imports: [ActionSelectorComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }],
    }).compileComponents();

    fixture = TestBed.createComponent(ActionSelectorComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display available actions", () => {
    const actions = [{ name: "action1" }, { name: "action2" }];
    policyServiceMock.availableActions.set(actions);
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll(".action-button");
    expect(actionElements.length).toBe(actions.length);
  });

  it("should select an action on click", () => {
    const actions = [{ name: "action1" }, { name: "action2" }];
    policyServiceMock.availableActions.set(actions);
    fixture.detectChanges();

    const actionElement = fixture.nativeElement.querySelector(".action-button");
    actionElement.click();

    expect(policyServiceMock.selectAction).toHaveBeenCalledWith(actions[0]);
  });
});
