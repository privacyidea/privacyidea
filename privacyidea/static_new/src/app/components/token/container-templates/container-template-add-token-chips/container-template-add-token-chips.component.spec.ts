import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateAddTokenChipsComponent } from "./container-template-add-token-chips.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";

describe("ContainerTemplateAddTokenChipsComponent", () => {
  let component: ContainerTemplateAddTokenChipsComponent;
  let fixture: ComponentFixture<ContainerTemplateAddTokenChipsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateAddTokenChipsComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
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
