
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PolicyDescriptionComponent } from "./policy-description.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("PolicyDescriptionComponent", () => {
  let component: PolicyDescriptionComponent;
  let fixture: ComponentFixture<PolicyDescriptionComponent>;
  let policyServiceMock: any;
  let documentationServiceMock: any;

  beforeEach(async () => {
    policyServiceMock = {
      isEditMode: signal(false),
      selectedPolicy: signal(null),
      updateSelectedPolicy: jasmine.createSpy("updateSelectedPolicy"),
    };

    documentationServiceMock = {
      openDocumentation: jasmine.createSpy("openDocumentation"),
    };

    await TestBed.configureTestingModule({
      imports: [PolicyDescriptionComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useValue: policyServiceMock },
        { provide: DocumentationService, useValue: documentationServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyDescriptionComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update policy description on input", () => {
    const description = "test description";
    component.updatePolicyDescription(description);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ description });
  });

  it("should open documentation on button click", () => {
    const page = "test-page";
    component.openDocumentation(page);
    expect(documentationServiceMock.openDocumentation).toHaveBeenCalledWith(page);
  });
});
