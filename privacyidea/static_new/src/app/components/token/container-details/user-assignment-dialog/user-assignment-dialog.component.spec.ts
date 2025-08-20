import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialogRef } from "@angular/material/dialog";

import { UserAssignmentDialogComponent } from "./user-assignment-dialog.component";

describe("UserAssignmentDialogComponent", () => {
  let fixture: ComponentFixture<UserAssignmentDialogComponent>;
  let component: UserAssignmentDialogComponent;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<
    MatDialogRef<UserAssignmentDialogComponent, string | null>
  >;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [UserAssignmentDialogComponent, NoopAnimationsModule],
      providers: [{ provide: MatDialogRef, useValue: dialogRefMock }]
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserAssignmentDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create the dialog", () => {
    expect(component).toBeTruthy();
  });

  it("should disable \"Assign All\" when PINs do not match", () => {
    component.pin.set("1234");
    component.pinRepeat.set("4321");
    fixture.detectChanges();

    const assignBtn = fixture.debugElement.query(
      By.css("mat-dialog-actions button[color=\"primary\"]")
    ).nativeElement as HTMLButtonElement;

    expect(assignBtn.disabled).toBe(true);
  });

  it("should enable \"Assign All\" when PINs match", () => {
    component.pin.set("1234");
    component.pinRepeat.set("1234");
    fixture.detectChanges();

    const assignBtn = fixture.debugElement.query(
      By.css("mat-dialog-actions button[color=\"primary\"]")
    ).nativeElement as HTMLButtonElement;

    expect(assignBtn.disabled).toBe(false);
  });

  it("should return the PIN on confirm", () => {
    component.pin.set("1234");
    component.pinRepeat.set("1234");

    component.onConfirm();

    expect(dialogRefMock.close).toHaveBeenCalledWith("1234");
  });

  it("should return null on cancel", () => {
    component.onCancel();

    expect(dialogRefMock.close).toHaveBeenCalledWith(null);
  });
});
