import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateTokenTypeSelectorComponent } from "./container-template-add-token-chips.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { HttpClientTestingModule } from "@angular/common/http/testing";

describe("ContainerTemplateTokenTypeSelectorComponent", () => {
  let component: ContainerTemplateTokenTypeSelectorComponent;
  let fixture: ComponentFixture<ContainerTemplateTokenTypeSelectorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateTokenTypeSelectorComponent, NoopAnimationsModule, HttpClientTestingModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateTokenTypeSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
