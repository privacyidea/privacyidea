import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ConfirmationDialogComponent } from "./confirmation-dialog.component";
import { MAT_DIALOG_DATA } from "@angular/material/dialog";

describe("ConfirmationDialogComponent", () => {
  let component: ConfirmationDialogComponent;
  let fixture: ComponentFixture<ConfirmationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serialList: ["Mock serial"],
            title: "Mock title",
            action: "Mock action",
            type: "Mock type"
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
