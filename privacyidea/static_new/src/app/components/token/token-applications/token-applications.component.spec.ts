import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenApplicationsComponent } from './token-applications.component';
import { TokenApplicationsSshComponent } from './token-applications-ssh/token-applications-ssh.component';
import { TokenApplicationsOfflineComponent } from './token-applications-offline/token-applications-offline.component';
import { MatSelectModule } from '@angular/material/select';
import { signal, WritableSignal } from '@angular/core';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TokenSelectedContentKey } from '../token.component';

describe('TokenApplications', () => {
  let component: TokenApplicationsComponent;
  let fixture: ComponentFixture<TokenApplicationsComponent>;
  let tokenSerial: WritableSignal<string>;
  let selectedContent: WritableSignal<TokenSelectedContentKey>;

  beforeEach(async () => {
    tokenSerial = signal('test-serial');
    selectedContent = signal({} as TokenSelectedContentKey);

    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsSshComponent,
        TokenApplicationsOfflineComponent,
        MatSelectModule,
        TokenApplicationsComponent,
        BrowserAnimationsModule,
      ],
      providers: [provideHttpClient(withInterceptorsFromDi())],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsComponent);
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

  it('should set token serial and selected content on tokenSelected', () => {
    component.tokenSelected('testSerial');
    expect(component.tokenSerial()).toBe('testSerial');
    expect(component.selectedContent()).toBe('token_details');
  });

  it('should update tokenSerial input', () => {
    component.tokenSerial.set('new-serial');
    expect(component.tokenSerial()).toBe('new-serial');
  });

  it('should update selectedContent input', () => {
    const newContent: TokenSelectedContentKey = 'token_details';
    component.selectedContent.set(newContent);
    expect(component.selectedContent()).toBe(newContent);
  });
});
