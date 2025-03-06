import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplications } from './token-applications';
import { TokenApplicationsSsh } from './token-applications-ssh/token-applications-ssh';
import { TokenApplicationsOffline } from './token-applications-offline/token-applications-offline';
import { MatSelectModule } from '@angular/material/select';
import { WritableSignal, signal } from '@angular/core';
import { TokenSelectedContent } from '../token.component';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('TokenApplications', () => {
  let component: TokenApplications;
  let fixture: ComponentFixture<TokenApplications>;
  let tokenSerial: WritableSignal<string>;
  let selectedContent: WritableSignal<TokenSelectedContent>;

  beforeEach(async () => {
    tokenSerial = signal('test-serial');
    selectedContent = signal({} as TokenSelectedContent);

    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsSsh,
        TokenApplicationsOffline,
        MatSelectModule,
        TokenApplications,
        BrowserAnimationsModule,
      ],
      providers: [provideHttpClient(withInterceptorsFromDi())],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplications);
    component = fixture.componentInstance;
    component.tokenSerial = tokenSerial;
    component.selectedContent = selectedContent;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have default selectedApplicationType as "ssh"', () => {
    expect(component.selectedApplicationType()).toBe('ssh');
  });

  it('should update tokenSerial input', () => {
    component.tokenSerial.set('new-serial');
    expect(component.tokenSerial()).toBe('new-serial');
  });

  it('should update selectedContent input', () => {
    const newContent: TokenSelectedContent = 'token_details';
    component.selectedContent.set(newContent);
    expect(component.selectedContent()).toBe(newContent);
  });
});
