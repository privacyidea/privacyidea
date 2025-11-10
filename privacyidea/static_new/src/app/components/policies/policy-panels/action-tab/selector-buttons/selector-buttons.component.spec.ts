import { ComponentFixture, TestBed } from "@angular/core/testing";
import { SelectorButtons } from "./selector-buttons.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
// import "@angular/localize/init";

describe("BoolSelectButtonsComponent", () => {
  let component: SelectorButtons<any>;
  let fixture: ComponentFixture<SelectorButtons<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectorButtons, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectorButtons);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("initialValue", true);
    component.values = [true, false];
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display buttons for each value", () => {
    fixture.detectChanges();
    const buttons = fixture.nativeElement.querySelectorAll("button");
    expect(buttons.length).toBe(component.values.length);
  });

  it("should emit value on button click", () => {
    jest.spyOn(component.onSelect, "emit");
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector("button");
    button.click();
    expect(component.onSelect.emit).toHaveBeenCalledWith(component.values[0]);
  });

  it("should set the selected value on init", () => {
    fixture.componentRef.setInput("initialValue", false);
    fixture.detectChanges();
    expect(component.selectedValue()).toBe(false);
  });
});
