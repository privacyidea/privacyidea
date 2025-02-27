import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollPushComponent } from './enroll-push.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('EnrollPushComponent', () => {
  let component: EnrollPushComponent;
  let fixture: ComponentFixture<EnrollPushComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPushComponent, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPushComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
