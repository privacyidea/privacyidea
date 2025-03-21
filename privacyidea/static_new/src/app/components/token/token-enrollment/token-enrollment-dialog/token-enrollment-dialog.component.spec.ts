import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  MAT_DIALOG_DATA,
  MatDialog,
  MatDialogRef,
} from '@angular/material/dialog';
import { TokenEnrollmentDialogComponent } from './token-enrollment-dialog.component';
import { of } from 'rxjs';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('TokenEnrollmentDialogComponent', () => {
  let component: TokenEnrollmentDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentDialogComponent>;
  let matDialogSpy: jasmine.SpyObj<MatDialog>;
  let matDialogRefSpy: jasmine.SpyObj<
    MatDialogRef<ConfirmationDialogComponent>
  >;

  matDialogRefSpy = jasmine.createSpyObj('MatDialogRef', [
    'close',
    'afterClosed',
  ]);
  matDialogSpy = jasmine.createSpyObj('MatDialog', ['open']);
  matDialogRefSpy.afterClosed.and.returnValue(of(true));

  beforeEach(async () => {
    matDialogSpy.open.and.returnValue({
      afterClosed: () => of(true),
    } as MatDialogRef<ConfirmationDialogComponent>);

    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentDialogComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
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
