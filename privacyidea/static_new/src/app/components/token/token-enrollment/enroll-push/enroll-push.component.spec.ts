import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollPushComponent } from './enroll-push.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollPushComponent', () => {
  let component: EnrollPushComponent;
  let fixture: ComponentFixture<EnrollPushComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPushComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPushComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
