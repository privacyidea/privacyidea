import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnrollSshkeyComponent } from './enroll-sshkey.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('EnrollSshkeyComponent', () => {
  let component: EnrollSshkeyComponent;
  let fixture: ComponentFixture<EnrollSshkeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSshkeyComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSshkeyComponent);
    component = fixture.componentInstance;
    component.sshPublicKey = signal('');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
