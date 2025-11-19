import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateEditComponent } from "./container-template-new.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatExpansionModule } from "@angular/material/expansion";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";

describe("ContainerTemplateEditComponent", () => {
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

  describe("existing template", () => {
    const templateName = "Test Template";

    beforeEach(() => {
      fixture.componentRef.setInput("template", { name: templateName });
      fixture.detectChanges();
    });

    it("should display the template name", () => {
      expect(fixture.nativeElement).toBeTruthy();
      const templateNameElement = fixture.nativeElement.querySelector(".template-name");
      expect(templateNameElement).toBeTruthy();
      expect(templateNameElement.textContent).toContain(templateName);
    });

    it("should select template on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(templateServiceMock.selectTemplateByName).toHaveBeenCalledWith(templateName);
    });
  });

  describe("new template", () => {
    beforeEach(() => {
      fixture.componentRef.setInput("isNew", true);
      fixture.detectChanges();
    });

    it("should initialize new template on expansion", () => {
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel");
      panel.dispatchEvent(new Event("opened"));
      fixture.detectChanges();
      expect(templateServiceMock.initializeNewTemplate).toHaveBeenCalled();
    });
  });
});
