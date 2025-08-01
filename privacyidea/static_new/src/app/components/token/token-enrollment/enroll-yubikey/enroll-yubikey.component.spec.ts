import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EnrollYubikeyComponent } from './enroll-yubikey.component';
import { provideHttpClient } from '@angular/common/http';

describe('EnrollYubikeyComponent', () => {
  let component: EnrollYubikeyComponent;
  let fixture: ComponentFixture<EnrollYubikeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient()],
      imports: [EnrollYubikeyComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubikeyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
