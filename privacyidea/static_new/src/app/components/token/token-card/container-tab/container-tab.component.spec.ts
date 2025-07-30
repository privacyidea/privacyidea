import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerTabComponent } from './container-tab.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import {
  BrowserAnimationsModule,
  provideNoopAnimations,
} from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

describe('ContainerTabComponent', () => {
  let component: ContainerTabComponent;
  let fixture: ComponentFixture<ContainerTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTabComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: '123' }),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTabComponent);
    component = fixture.componentInstance;
    component.containerSerial = signal('Mock serial');
    component.states = signal(['active']);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
