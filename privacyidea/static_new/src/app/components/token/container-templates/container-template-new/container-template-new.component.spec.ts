import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatExpansionModule } from "@angular/material/expansion";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { ContainerTemplateEditComponent } from "../container-template-edit/container-template-edit.component";

describe("ContainerTemplateNewComponent", () => {
  let component: ContainerTemplateEditComponent;
  let fixture: ComponentFixture<ContainerTemplateEditComponent>;
  let templateServiceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditComponent, NoopAnimationsModule, MatExpansionModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditComponent);
    templateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
