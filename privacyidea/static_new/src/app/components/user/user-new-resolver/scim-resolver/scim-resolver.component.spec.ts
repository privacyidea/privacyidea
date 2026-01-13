import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ScimResolverComponent } from "./scim-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("ScimResolverComponent", () => {
  let component: ScimResolverComponent;
  let componentRef: ComponentRef<ScimResolverComponent>;
  let fixture: ComponentFixture<ScimResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScimResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ScimResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose controls via signal", () => {
    const controls = component.controls();
    expect(controls).toEqual(expect.objectContaining({
      Authserver: component.authServerControl,
      Resourceserver: component.resourceServerControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      Authserver: "http://auth",
      Resourceserver: "http://resource",
      Client: "client1",
      Secret: "secret1",
      Mapping: "{}"
    });

    fixture.detectChanges();

    expect(component.authServerControl.value).toBe("http://auth");
    expect(component.resourceServerControl.value).toBe("http://resource");
    expect(component.clientControl.value).toBe("client1");
    expect(component.secretControl.value).toBe("secret1");
    expect(component.mappingControl.value).toBe("{}");
  });
});
