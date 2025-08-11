import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EnrollWebauthnComponent } from './enroll-webauthn.component';
import { provideHttpClient } from '@angular/common/http';

describe('EnrollWebauthnComponent', () => {
  let component: EnrollWebauthnComponent;
  let fixture: ComponentFixture<EnrollWebauthnComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient()],
      imports: [EnrollWebauthnComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollWebauthnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
