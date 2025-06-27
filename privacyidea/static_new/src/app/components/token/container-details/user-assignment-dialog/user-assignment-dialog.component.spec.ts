import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserAssignmentDialogComponent } from './user-assignment-dialog.component';
import { MatDialogRef } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('UserAssignmentDialogComponent', () => {
  let component: UserAssignmentDialogComponent;
  let fixture: ComponentFixture<UserAssignmentDialogComponent>;
  let dialogRefSpy: jasmine.SpyObj<
    MatDialogRef<UserAssignmentDialogComponent, string | null>
  >;

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [UserAssignmentDialogComponent, NoopAnimationsModule],
      providers: [{ provide: MatDialogRef, useValue: dialogRefSpy }],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserAssignmentDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the dialog', () => {
    expect(component).toBeTruthy();
  });

  it('should disable Assign All if PINs do not match', () => {
    component.pin.set('1234');
    component.pinRepeat.set('4321');
    fixture.detectChanges();
    const assignBtn = fixture.debugElement.queryAll(By.css('button'))[1]
      .nativeElement;
    expect(assignBtn.disabled).toBeTrue();
  });

  it('should enable Assign All if PINs match', () => {
    component.pin.set('1234');
    component.pinRepeat.set('1234');
    fixture.detectChanges();
    const assignBtn = fixture.debugElement.queryAll(By.css('button'))[1]
      .nativeElement;
    expect(assignBtn.disabled).toBeFalse();
  });

  it('should return true on confirm', () => {
    component.pin.set('1234');
    component.pinRepeat.set('1234');
    component.onConfirm();
    expect(dialogRefSpy.close).toHaveBeenCalledWith('1234');
  });

  it('should return false on cancel', () => {
    component.onCancel();
    expect(dialogRefSpy.close).toHaveBeenCalledWith(null);
  });
});
