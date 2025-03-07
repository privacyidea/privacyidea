import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConfirmGetSerialDialogComponent } from './confirm-get-serial-dialog.component';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

describe('ConfirmationDialogComponent', () => {
  let component: ConfirmGetSerialDialogComponent;
  let fixture: ComponentFixture<ConfirmGetSerialDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmGetSerialDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serial_list: ['Mock serial'],
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmGetSerialDialogComponent);
    component = fixture.componentInstance;
    component.data = {
      numberOfTokens: 42,
      onAbort: jasmine.createSpy(),
      onConfirm: jasmine.createSpy(),
    };
    fixture.detectChanges();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('should display the correct number of tokens', () => {
    const compiled = fixture.nativeElement;
    expect(compiled.querySelector('.token-count').textContent).toContain(
      component.data.numberOfTokens,
    );
  });
  it('should call onAbort when abort button is clicked', () => {
    const button = fixture.nativeElement.querySelector('.abort-button');
    button.click();
    expect(component.data.onAbort).toHaveBeenCalled();
  });
  it('should call onConfirm when confirm button is clicked', () => {
    const button = fixture.nativeElement.querySelector('.confirm-button');
    button.click();
    expect(component.data.onConfirm).toHaveBeenCalled();
  });
});
