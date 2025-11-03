import { ComponentFixture, TestBed } from "@angular/core/testing";

import { UserDetailsPinDialogComponent } from "./user-details-pin-dialog.component";
import { By } from "@angular/platform-browser";
import { MatDialogRef } from "@angular/material/dialog";

describe("UserDetailsPinDialogComponent", () => {
  let component: UserDetailsPinDialogComponent;
  let fixture: ComponentFixture<UserDetailsPinDialogComponent>;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<
    MatDialogRef<UserDetailsPinDialogComponent, string | null>
  >;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsPinDialogComponent],
      providers: [{ provide: MatDialogRef, useValue: dialogRefMock }]
    })
      .compileComponents();

    fixture = TestBed.createComponent(UserDetailsPinDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });


  it("should disable \"assign\" when PINs do not match", () => {
    component.pin.set("1234");
    component.pinRepeat.set("4321");
    fixture.detectChanges();

    const assignBtn = fixture.debugElement.query(
      By.css("mat-dialog-actions button[color=\"primary\"]")
    ).nativeElement as HTMLButtonElement;

    expect(assignBtn.disabled).toBe(true);
  });

  it("should enable \"assign\" when PINs match", () => {
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

  it("should close on cancel", () => {
    component.onCancel();

    expect(dialogRefMock.close).toHaveBeenCalled();
  });
});
