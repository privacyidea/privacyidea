import { ComponentFixture, TestBed } from "@angular/core/testing";
import { HttpResolverComponent } from "./http-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("HttpResolverComponent", () => {
  let component: HttpResolverComponent;
  let componentRef: ComponentRef<HttpResolverComponent>;
  let fixture: ComponentFixture<HttpResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HttpResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(HttpResolverComponent);
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
      endpoint: component.endpointControl,
      method: component.methodControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      endpoint: "http://test",
      method: "POST",
      attribute_mapping: { "username": "user" }
    });

    fixture.detectChanges();

    expect(component.endpointControl.value).toBe("http://test");
    expect(component.methodControl.value).toBe("POST");
    expect(component["mappingRows"]()).toContainEqual({ privacyideaAttr: "username", userStoreAttr: "user" });
  });

  it("should add and remove mapping rows", () => {
    const initialCount = component["mappingRows"]().length;
    component.addMappingRow();
    expect(component["mappingRows"]().length).toBe(initialCount + 1);

    component.removeMappingRow(0);
    expect(component["mappingRows"]().length).toBe(initialCount);
  });


  it("should handle privacyidea attribute change", () => {
    component.addMappingRow();
    const index = component["mappingRows"]().length - 1;

    component["mappingRows"]()[index].privacyideaAttr = component["CUSTOM_ATTR_VALUE"];
    component.onPrivacyIdeaAttrChanged(index);

    expect(component["mappingRows"]()[index].privacyideaAttr).toBe(component["CUSTOM_ATTR_VALUE"]);
  });

});
