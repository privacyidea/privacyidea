import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateAddTokenChipsComponent } from "./container-template-add-token-chips.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { HttpClientTestingModule } from "@angular/common/http/testing";

describe("anyTypeSelectorComponent", () => {
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

  it("addToken should emit onAddToken with the correct token type", () => {
    jest.spyOn(component.onAddToken, "emit");
    const tokenType = "totp";
    component.addToken(tokenType);
    expect(component.onAddToken.emit).toHaveBeenCalledWith(tokenType);
  });
});
