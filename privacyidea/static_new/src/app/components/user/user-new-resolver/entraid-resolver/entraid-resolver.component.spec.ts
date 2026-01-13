import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EntraidResolverComponent } from "./entraid-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("EntraidResolverComponent", () => {
  let component: EntraidResolverComponent;
  let componentRef: ComponentRef<EntraidResolverComponent>;
  let fixture: ComponentFixture<EntraidResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntraidResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(EntraidResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize default data on creation", () => {
    componentRef.setInput("data", {});
    fixture.detectChanges();
    expect(component.baseUrlControl.value).toBe("https://graph.microsoft.com/v1.0");
    expect(component.authorityControl.value).toBe("https://login.microsoftonline.com/{tenant}");
    expect(component.configGetUserListGroup.value.endpoint).toBe("/users");
  });
});
