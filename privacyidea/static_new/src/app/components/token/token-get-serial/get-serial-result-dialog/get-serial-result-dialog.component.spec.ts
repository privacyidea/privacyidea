import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GetSerialResultDialogComponent } from './get-serial-result-dialog.component';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

describe('ConfirmationDialogComponent', () => {
  let component: GetSerialResultDialogComponent;
  let fixture: ComponentFixture<GetSerialResultDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GetSerialResultDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serial_list: ['Mock serial'],
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(GetSerialResultDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
