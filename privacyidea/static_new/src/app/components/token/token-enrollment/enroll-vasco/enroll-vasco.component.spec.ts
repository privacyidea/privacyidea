import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollVascoComponent } from './enroll-vasco.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollVascoComponent', () => {
  let component: EnrollVascoComponent;
  let fixture: ComponentFixture<EnrollVascoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollVascoComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollVascoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
