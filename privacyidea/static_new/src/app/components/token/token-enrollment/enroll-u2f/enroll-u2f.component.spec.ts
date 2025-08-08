import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollU2fComponent } from './enroll-u2f.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollU2fComponent', () => {
  let component: EnrollU2fComponent;
  let fixture: ComponentFixture<EnrollU2fComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollU2fComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollU2fComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
