import { ComponentFixture, TestBed } from "@angular/core/testing";
import { SqlResolverComponent } from "./sql-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("SqlResolverComponent", () => {
  let component: SqlResolverComponent;
  let componentRef: ComponentRef<SqlResolverComponent>;
  let fixture: ComponentFixture<SqlResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SqlResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SqlResolverComponent);
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
      Driver: component.driverControl,
      Server: component.serverControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      Driver: "mysql",
      Server: "localhost",
      Table: "users",
      Limit: 100,
      Map: "{}"
    });

    fixture.detectChanges();

    expect(component.driverControl.value).toBe("mysql");
    expect(component.serverControl.value).toBe("localhost");
    expect(component.tableControl.value).toBe("users");
    expect(component.limitControl.value).toBe(100);
    expect(component.mapControl.value).toBe("{}");
  });
});
