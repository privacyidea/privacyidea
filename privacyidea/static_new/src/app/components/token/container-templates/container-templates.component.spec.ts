import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplatesComponent } from "./container-templates.component";
import { ContainerTemplateService } from "../../../services/container-template/container-template.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplateEditComponent } from "./container-template-edit/container-template-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerTemplate } from "../../../services/container/container.service";

describe("ContainerTemplatesComponent", () => {
  let component: ContainerTemplatesComponent;
  let fixture: ComponentFixture<ContainerTemplatesComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesComponent, NoopAnimationsModule, ContainerTemplateEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplatesComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display a list of container templates", () => {
    const template1 = {
      name: "template1",
      container_type: "",
      default: false,
      template_options: {
        options: undefined,
        tokens: []
      }
    };
    const templates: ContainerTemplate[] = [template1, { ...template1, name: "template2" }];
    containerTemplateServiceMock.allContainerTemplates.set(templates);
    fixture.detectChanges();

    const templateElements = fixture.nativeElement.querySelectorAll(".container-template-card");
    expect(templateElements.length).toBe(templates.length + 1); // +1 for the "new template" panel
    expect(templateElements[1].textContent).toContain("template1");
    expect(templateElements[2].textContent).toContain("template2");
  });

  it("should display a new template panel", () => {
    fixture.detectChanges();
    const newTemplatePanel = fixture.nativeElement.querySelector(".container-template-card");
    expect(newTemplatePanel).toBeTruthy();
    expect(newTemplatePanel.textContent).toContain("New Template");
  });
});
