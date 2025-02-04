import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  MatDialog,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';
import { TokenEnrollmentDialogComponent } from './token-enrollment-dialog.component';
import { of } from 'rxjs';
import { ConfirmationDialogComponent } from '../../token-card/container-tab/confirmation-dialog/confirmation-dialog.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('TokenEnrollmentDialogComponent', () => {
  let component: TokenEnrollmentDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentDialogComponent>;
  let matDialogSpy: jasmine.SpyObj<MatDialog>;
  let matDialogRefSpy: jasmine.SpyObj<
    MatDialogRef<ConfirmationDialogComponent>
  >;

  matDialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);
  matDialogSpy = jasmine.createSpyObj('MatDialog', ['open']);

  beforeEach(async () => {
    matDialogSpy.open.and.returnValue({
      afterClosed: () => of(true),
    } as MatDialogRef<ConfirmationDialogComponent>);

    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentDialogComponent, BrowserAnimationsModule],
      providers: [
        { provide: MatDialog, useValue: matDialogSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            response: {
              detail: {
                serial: 'Mock serial',
                googleurl: {
                  img: 'Mock img',
                },
                otpkey: {
                  value: 'Mock value',
                  value_b32: 'Mock value_b32',
                },
              },
            },
          },
        },
        { provide: MatDialogRef, useValue: matDialogRefSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
