import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplatesComponent } from "./container-templates.component";
import { ContainerTemplateService } from "../../../services/container-template/container-template.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplateEditComponent } from "./container-template-edit/container-template-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockContainerTemplateService } from "../../../../testing/mock-services/mock-container-template-service";

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
});
