import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContainerRegistrationDialogComponent } from './container-registration-dialog.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { of } from 'rxjs';
import { signal } from '@angular/core';

describe('ContainerRegistrationDialogComponent', () => {
  let component: ContainerRegistrationDialogComponent;
  let fixture: ComponentFixture<ContainerRegistrationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: { afterClosed: () => of(true) } },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            response: {
              result: {
                value: { container_url: { img: '' } },
              },
            },
            containerSerial: signal(''),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
