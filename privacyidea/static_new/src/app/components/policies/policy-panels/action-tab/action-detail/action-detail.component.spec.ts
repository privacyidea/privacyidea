
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActionDetailComponent } from "./action-detail.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("ActionDetailComponent", () => {
  let component: ActionDetailComponent;
  let fixture: ComponentFixture<ActionDetailComponent>;
  let policyServiceMock: any;
  let documentationServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      isEditMode: signal(false),
      selectedActionDetail: signal(null),
      selectedAction: signal(null),
      actionValueIsValid: jasmine.createSpy("actionValueIsValid").and.returnValue(true),
      updateActionInSelectedPolicy: jasmine.createSpy("updateActionInSelectedPolicy"),
    };

    documentationServiceMock = {
      policyActionDocumentation: signal(null),
    };

    await TestBed.configureTestingModule({
      imports: [ActionDetailComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useValue: policyServiceMock },
        { provide: DocumentationService, useValue: documentationServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ActionDetailComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display documentation and notes", () => {
    const docu = { actionDocu: ["doc1"], actionNotes: ["note1"] };
    documentationServiceMock.policyActionDocumentation.set(docu);
    fixture.detectChanges();

    component.toggleContent("docu");
    fixture.detectChanges();
    const docuElement = fixture.nativeElement.querySelector(".docu-content");
    expect(docuElement).toBeTruthy();

    component.toggleContent("notes");
    fixture.detectChanges();
    const notesElement = fixture.nativeElement.querySelector(".notes-content");
    expect(notesElement).toBeTruthy();
  });

  it("should apply changes when input is valid", () => {
    policyServiceMock.selectedActionDetail.set({ name: "test", type: "string" });
    policyServiceMock.selectedAction.set({ name: "test", value: "value" });
    fixture.detectChanges();

    component.applyChanges();
    expect(policyServiceMock.updateActionInSelectedPolicy).toHaveBeenCalled();
    expect(policyServiceMock.selectedAction.set).toHaveBeenCalledWith(null);
  });
});
