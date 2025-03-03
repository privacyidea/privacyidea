import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollTiqrComponent } from './enroll-tiqr.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollTiqrComponent', () => {
  let component: EnrollTiqrComponent;
  let fixture: ComponentFixture<EnrollTiqrComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTiqrComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTiqrComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
