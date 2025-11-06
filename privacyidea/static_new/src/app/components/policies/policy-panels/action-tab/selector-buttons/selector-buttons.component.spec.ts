
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BoolSelectButtonsComponent } from "./selector-buttons.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { input } from "@angular/core";

describe("BoolSelectButtonsComponent", () => {
  let component: BoolSelectButtonsComponent<any>;
  let fixture: ComponentFixture<BoolSelectButtonsComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoolSelectButtonsComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(BoolSelectButtonsComponent);
    component = fixture.componentInstance;
    component.initialValue = input(true);
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
    spyOn(component.onSelect, "emit");
    fixture.detectChanges();

    const button = fixture.nativeElement.querySelector("button");
    button.click();

    expect(component.onSelect.emit).toHaveBeenCalledWith(component.values[0]);
  });

  it("should set the selected value on init", () => {
    component.initialValue = input(false);
    fixture.detectChanges();
    expect(component.selectedValue()).toBe(false);
  });
});
