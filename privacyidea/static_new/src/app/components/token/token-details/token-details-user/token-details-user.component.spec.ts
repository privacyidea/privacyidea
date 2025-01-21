import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenDetailsUserComponent } from './token-details-user.component';
import { TokenService } from '../../../../services/token/token.service';
import { AppComponent } from '../../../../app.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('TokenDetailsUserComponent', () => {
  let component: TokenDetailsUserComponent;
  let tokenService: TokenService;
  let fixture: ComponentFixture<TokenDetailsUserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TokenDetailsUserComponent,
        AppComponent,
        BrowserAnimationsModule,
      ],
      providers: [
        TokenService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    tokenService = TestBed.inject(TokenService);
    fixture = TestBed.createComponent(TokenDetailsUserComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.isEditingUser = signal(false);
    component.setPinValue = signal('');
    component.setPinValue = signal('');
    component.repeatPinValue = signal('');
    component.selectedUserRealm = signal('');
    component.userOptions = signal(['user1', 'user2', 'admin']);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should assign user', () => {
    component.selectedUsername.set('testUser');
    component.selectedUserRealm.set('testRealm');
    component.setPinValue.set('1234');
    component.repeatPinValue.set('1234');

    spyOn(tokenService, 'assignUser').and.callThrough();
    component.saveUser();
    expect(tokenService.assignUser).toHaveBeenCalledWith(
      'Mock serial',
      'testUser',
      'testRealm',
      '1234'
    );
  });

  it('should not assign user if PINs do not match', () => {
    component.setPinValue.set('1234');
    component.repeatPinValue.set('5678');

    spyOn(tokenService, 'assignUser').and.callThrough();
    component.saveUser();
    expect(tokenService.assignUser).not.toHaveBeenCalled();
  });

  it('should filter user options correctly', () => {
    const result = component['_filterUserOptions']('user');
    expect(result).toEqual(['user1', 'user2']);
  });
});
