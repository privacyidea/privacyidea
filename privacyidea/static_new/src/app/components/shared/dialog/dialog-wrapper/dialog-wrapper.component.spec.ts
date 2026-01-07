import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DialogWrapperComponent } from "./dialog-wrapper.component";
import { CUSTOM_ELEMENTS_SCHEMA } from "@angular/core";

describe("DialogWrapperComponent", () => {
  let component: DialogWrapperComponent;
  let fixture: ComponentFixture<DialogWrapperComponent>;
  let nativeElement: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DialogWrapperComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DialogWrapperComponent);
    component = fixture.componentInstance;
    nativeElement = fixture.nativeElement;
    fixture.componentRef.setInput("title", "Test Title");
    fixture.componentRef.setInput("actions", [
      { id: "confirm", label: "Confirm", type: "confirm" },
      { id: "cancel", label: "Cancel", type: "cancel" },
    ]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the title", () => {
    const titleEl = nativeElement.querySelector("h2");
    expect(titleEl?.textContent).toContain("Test Title");
  });

  it("should display the icon", () => {
    fixture.componentRef.setInput("icon", "test_icon");
    fixture.detectChanges();
    const iconEl = nativeElement.querySelector("mat-icon");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.textContent).toBe("test_icon");
  });

  it("should not display the icon", () => {
    const iconEl = nativeElement.querySelector("mat-icon");
    expect(iconEl).toBeFalsy();
  });

  it("should show the close button when showCloseButton is true", () => {
    const closeButton = nativeElement.querySelector(".pi-close-button");
    expect(closeButton).toBeTruthy();
  });

  it("should not show the close button when showCloseButton is false", () => {
    fixture.componentRef.setInput("showCloseButton", false);
    fixture.detectChanges();
    const closeButton = nativeElement.querySelector(".pi-close-button");
    expect(closeButton).toBeFalsy();
  });

  it("should emit close event when close button is clicked", () => {
    jest.spyOn(component, "onCloseClick");
    const closeButton = nativeElement.querySelector(".pi-close-button") as HTMLButtonElement;
    closeButton.click();
    expect(component.onCloseClick).toHaveBeenCalled();
  });

  it("should render action buttons", () => {
    const actionButtons = nativeElement.querySelectorAll(".pi-btn");
    expect(actionButtons.length).toBe(2);
    expect(actionButtons[0].textContent?.trim()).toBe("Confirm");
    expect(actionButtons[1].textContent?.trim()).toBe("Cancel");
  });

  it("should emit onAction event with correct value when an action button is clicked", () => {
    jest.spyOn(component, "onActionClick");
    const actionButtons = nativeElement.querySelectorAll(".pi-btn") as NodeListOf<HTMLButtonElement>;
    actionButtons[0].click();
    expect(component.onActionClick).toHaveBeenCalledWith({ id: "confirm", label: "Confirm", type: "confirm" });
  });

  it("should apply correct classes to action buttons", () => {
    const actionButtons = nativeElement.querySelectorAll(".pi-btn");
    expect(actionButtons[0].classList).toContain("dialog-action-button-default");
    expect(actionButtons[1].classList).toContain("dialog-action-button-cancel");
  });

  it("should throw an error if no actions and no close button", () => {
    const fixtureWrapper = TestBed.createComponent(DialogWrapperComponent);
    const componentWrapper = fixtureWrapper.componentInstance;
    fixtureWrapper.componentRef.setInput("actions", []);
    fixtureWrapper.componentRef.setInput("showCloseButton", false);
    expect(() => fixtureWrapper.detectChanges()).toThrow("Dialog must have at least one action or a close button.");
  });
});
