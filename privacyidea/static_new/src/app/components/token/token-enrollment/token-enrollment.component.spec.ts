import { of } from 'rxjs';
import { signal } from '@angular/core';
import { TokenEnrollmentComponent } from './token-enrollment.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { RealmService } from '../../../services/realm/realm.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';
import { MatDialog } from '@angular/material/dialog';
import { VersionService } from '../../../services/version/version.service';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenSelectedContent } from '../token.component';

class MockTokenService {
  private _tokenTypeOptions = [
    { key: 'yubikey', info: 'Mock info for yubikey' },
    { key: 'other', info: 'Other token info' },
  ];

  tokenTypeOptions() {
    return this._tokenTypeOptions;
  }

  enrollToken(options: any) {
    return of({ detail: { serial: '1234', rollout_state: 'done' } });
  }

  pollTokenRolloutState(tokenSerial: string, startTime: number) {
    return of({ result: { value: { tokens: [{ rollout_state: 'done' }] } } });
  }
}

class MockContainerService {
  selectedContainer = signal('Mock container serial');
  filteredContainerOptions = signal(['Mock container serial']);

  resetContainerSelection() {}

  getContainerData(options: any) {
    return of({
      result: { value: { containers: [{ serial: 'Mock container serial' }] } },
    });
  }
}

class MockRealmService {
  realmOptions = signal([]);

  resetRealmSelection() {}

  getRealms() {
    return of({ result: { value: { realm1: {} } } });
  }

  getDefaultRealm() {
    return of('defaultRealm');
  }
}

class MockNotificationService {
  openSnackBar(message: string) {}
}

class MatDialogStub {
  open() {
    return { afterClosed: () => of(true) };
  }

  closeAll() {}
}

class MockVersionService {}

class MockUserService {
  selectedUserRealm = signal('Mock realm');
  selectedUsername = signal('Mock username');
  userOptions = signal(['user1', 'user2', 'admin']);
  filteredUserOptions = signal(['user1', 'user2', 'admin']);

  resetUserSelection() {
    this.selectedUsername.set('');
    this.selectedUserRealm.set('');
  }
}

describe('TokenEnrollmentComponent', () => {
  let component: TokenEnrollmentComponent;
  let fixture: ComponentFixture<TokenEnrollmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: UserService, useClass: MockUserService },
        { provide: MatDialog, useClass: MatDialogStub },
        { provide: VersionService, useClass: MockVersionService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock container serial');
    component.selectedContent = signal({} as TokenSelectedContent);
    component.isProgrammaticChange = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
