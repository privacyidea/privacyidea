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
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
