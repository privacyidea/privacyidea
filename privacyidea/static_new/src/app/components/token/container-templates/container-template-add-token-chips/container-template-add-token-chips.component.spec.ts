import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateAddTokenChipsComponent } from "./container-template-add-token-chips.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { HttpClientTestingModule } from "@angular/common/http/testing";

describe("ContainerTemplateTokenTypeSelectorComponent", () => {
  let component: ContainerTemplateAddTokenChipsComponent;
  let fixture: ComponentFixture<ContainerTemplateAddTokenChipsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateAddTokenChipsComponent, NoopAnimationsModule, HttpClientTestingModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateAddTokenChipsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
