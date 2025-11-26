import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplateEditComponent } from "../container-template-edit/container-template-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row.component";

describe("TemplateAddedTokenRowComponent", () => {
  let component: TemplateAddedTokenRowComponent;
  let fixture: ComponentFixture<TemplateAddedTokenRowComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateAddedTokenRowComponent, NoopAnimationsModule, ContainerTemplateEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TemplateAddedTokenRowComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("updateToken should call editToken on containerTemplateService", () => {
    jest.spyOn(component.onEditToken, "emit");
    const tokenUpdate = { serial: "T-001", type: "totp" };
    component.updateToken(tokenUpdate);
    expect(component.onEditToken.emit).toHaveBeenCalledWith(tokenUpdate);
  });
  describe("onRemoveToken", () => {
    it("should call onRemoveToken emit with the correct token serial", () => {
      jest.spyOn(component.onRemoveToken, "emit");
      fixture.componentRef.setInput("index", 0);
      component.removeToken();
      expect(component.onRemoveToken.emit).toHaveBeenCalledWith(0);
    });

    it("should not call onRemoveToken emit if index is not valid", () => {
      jest.spyOn(component.onRemoveToken, "emit");
      fixture.componentRef.setInput("index", -1);
      component.removeToken();
      expect(component.onRemoveToken.emit).not.toHaveBeenCalled();
    });
  });
});
