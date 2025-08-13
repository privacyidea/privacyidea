import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EditButtonsComponent } from "./edit-buttons.component";
import { signal } from "@angular/core";

describe("EditButtonsComponent", () => {
  let component: EditButtonsComponent<any>;
  let fixture: ComponentFixture<EditButtonsComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditButtonsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(EditButtonsComponent);
    component = fixture.componentInstance;
    component.element = {
      keyMap: { key: "value", label: "label" },
      isEditing: signal(false)
    };
    component.isEditingUser = signal(false);
    component.isEditingInfo = signal(false);
    component.shouldHideEdit = signal(false);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
