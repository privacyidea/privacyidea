import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerDetailsComponent } from './container-details.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { TokenDetailsComponent } from '../token-details/token-details.component';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { ValidateService } from '../../../services/validate/validate.service';
import { of, throwError } from 'rxjs';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';

class MockTokenService {
  getTokenDetails() {
    return of({
      result: {
        value: {
          tokens: [
            {
              active: true,
              revoked: false,
              container_serial: 'Mock serial',
              realms: ['realm1', 'realm2'],
            },
          ],
        },
      },
    });
  }

  getRealms() {
    return of({ result: { value: ['realm1', 'realm2'] } });
  }

  resetFailCount() {
    return of(null);
  }

  assignUser() {
    return of(null);
  }

  unassignUser() {
    return of(null);
  }

  getTokenData() {
    return of({
      result: {
        value: {
          tokens: [
            {
              active: true,
              revoked: false,
              container_serial: 'Mock serial',
              realms: ['realm1', 'realm2'],
            },
          ],
        },
      },
    });
  }
}

class MockContainerService {
  getContainerData() {
    return of({
      result: {
        value: {
          containers: [{ serial: 'Mock serial' }, { serial: 'container2' }],
        },
      },
    });
  }

  addTokenToContainer() {
    return of(null);
  }

  getContainerDetails() {
    return of(null);
  }

  assignContainer() {
    return of(null);
  }

  unassignUser() {
    return of(null);
  }

  assignUser() {
    return of(null);
  }

  setContainerRealm() {
    return of(null);
  }

  setContainerDescription() {
    return of(null);
  }
}

class MockValidateService {
  testToken() {
    return of(null);
  }
}

class MockNotificationService {
  openSnackBar() {
    return of(null);
  }
}

class MockUserService {
  selectedUsername = signal('');
  selectedUserRealm = signal('');
  setDefaultRealm() {
    return of(null);
  }
  resetUserSelection() {
    this.selectedUsername.set('');
    this.selectedUserRealm.set('');
  }
}

describe('ContainerDetailsComponent', () => {
  let component: ContainerDetailsComponent;
  let fixture: ComponentFixture<ContainerDetailsComponent>;
  let tokenService: TokenService;
  let containerService: ContainerService;
  let userService: UserService;
  let validateService: ValidateService;
  let notificationService: NotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useValue: MockNotificationService },
        { provide: UserService, useClass: MockUserService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock serial');
    component.refreshContainerDetails = signal(false);
    component.infoData = signal([
      {
        keyMap: { key: 'info', label: 'Info' },
        value: { key1: 'value1', key2: 'value2' },
        isEditing: signal(false),
      },
    ]);
    component.userData = signal([
      {
        keyMap: { key: 'user', label: 'User' },
        value: { key1: 'value1', key2: 'value2' },
        isEditing: signal(false),
      },
    ]);
    component.realmOptions = signal(['realm1', 'realm2']);
    component.selectedContent = signal('token_details');
    tokenService = TestBed.inject(TokenService);
    containerService = TestBed.inject(ContainerService);
    validateService = TestBed.inject(ValidateService);
    notificationService = TestBed.inject(NotificationService);
    userService = TestBed.inject(UserService);

    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load token details on initialization', () => {
    spyOn(tokenService, 'getTokenDetails').and.callThrough();
    component.showContainerDetail().subscribe(() => {
      expect(tokenService.getTokenDetails).toHaveBeenCalledWith('Mock serial');
      expect(component.containerDetailData().length).toBeGreaterThan(0);
      expect(component.infoData().length).toBeGreaterThan(0);
      expect(component.realmOptions().length).toBeGreaterThan(0);
      expect(component.containerSerial()).toBe('Mock serial');
      expect(component.realmOptions().length).toBeGreaterThan(0);
      expect(component.states()).toBe(['active']);
    });
  });

  it('should handle errors when loading token details fails', () => {
    spyOn(tokenService, 'getTokenDetails').and.returnValue(
      throwError(() => new Error('Error fetching token details.')),
    );
    spyOn(console, 'error');
    component.showContainerDetail().subscribe({
      error: () => {
        expect(console.error).toHaveBeenCalledWith(
          'Failed to get token details. ',
          jasmine.any(Error),
        );
      },
    });
  });

  it('should handle empty data gracefully', () => {
    spyOn(containerService, 'getContainerDetails').and.returnValue(
      of({ result: { value: { tokens: [] } } }),
    );
    component.showContainerDetail().subscribe({
      next: () => {
        expect(component.containerDetailData().length).toBe(0);
      },
    });
  });

  it('should get container data', () => {
    spyOn(containerService, 'getContainerData').and.callThrough();
    component.showContainerDetail().subscribe(() => {
      expect(containerService.getContainerData).toHaveBeenCalledWith({
        page: 1,
        pageSize: 10,
      });
    });
  });

  it('should add token', () => {
    component.containerSerial = signal('container1');
    spyOn(containerService, 'addTokenToContainer').and.callThrough();
    component.addTokenToContainer({
      serial: 'Mock Serial',
      tokentype: 'hotp',
      active: true,
      username: 'username',
    });
    expect(containerService.addTokenToContainer).toHaveBeenCalledWith(
      'container1',
      'Mock Serial',
    );
  });

  it('should filter user options correctly', () => {
    //TODO
  });

  it('should return true for description and realms in isEditableElement', () => {
    expect(component.isEditableElement('description')).toBeTrue();
    expect(component.isEditableElement('realms')).toBeTrue();
    expect(component.isEditableElement('otherKey')).toBeFalse();
  });

  it('should toggle edit mode for realms and call setContainerRealm on save', () => {
    const setRealmSpy = spyOn(
      containerService,
      'setContainerRealm',
    ).and.returnValue(of(Object));

    component.containerDetailData.set([
      {
        keyMap: { label: 'Realms', key: 'realms' },
        value: ['realm1'],
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];

    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBeTrue();

    component.selectedRealms.set(['realm1', 'realm2']);
    component.saveContainerEdit(element);

    expect(setRealmSpy).toHaveBeenCalledWith('Mock serial', [
      'realm1',
      'realm2',
    ]);
    expect(element.isEditing()).toBeFalse();
  });

  it('should toggle edit mode for description and call setContainerDescription on save', () => {
    const setDescSpy = spyOn(
      containerService,
      'setContainerDescription',
    ).and.returnValue(of(Object));

    component.containerDetailData.set([
      {
        keyMap: { label: 'Description', key: 'description' },
        value: 'Old description',
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];
    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBeTrue();

    component.containerDetailData.set([
      {
        keyMap: { label: 'Description', key: 'description' },
        value: 'New description from UI',
        isEditing: signal(false),
      },
    ]);

    component.saveContainerEdit(element);
    expect(setDescSpy).toHaveBeenCalledWith(
      'Mock serial',
      'New description from UI',
    );
    expect(element.isEditing()).toBeFalse();
  });

  it('should enter user edit mode, call saveUser on save, and exit edit mode', () => {
    const assignUserSpy = spyOn(containerService, 'assignUser').and.returnValue(
      of(Object),
    );

    component.userData.set([
      {
        keyMap: { label: 'User Name', key: 'user_name' },
        value: '',
        isEditing: signal(false),
      },
    ]);

    const element = component.userData()[0];
    expect(component.isEditingUser()).toBeFalse();

    component.toggleContainerEdit(element);
    expect(component.isEditingUser()).toBeTrue();

    userService.selectedUsername.set('alice');
    userService.selectedUserRealm.set('realmUser');

    component.saveUser();
    expect(assignUserSpy).toHaveBeenCalledWith({
      containerSerial: 'Mock serial',
      username: 'alice',
      userRealm: 'realmUser',
    });
    expect(component.isEditingUser()).toBeFalse();
  });

  it('should handle cancel action when editing realms', () => {
    component.selectedRealms.set(['realm1']);
    component.containerDetailData.set([
      {
        keyMap: { label: 'Realms', key: 'realms' },
        value: 'Old description',
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];
    component.cancelContainerEdit(element);
    expect(component.selectedRealms()).toEqual([]);
  });

  it('should handle cancel action for other fields by re-calling showContainerDetail', () => {
    const showDetailSpy = spyOn(
      component,
      'showContainerDetail',
    ).and.callThrough();
    const element = component.containerDetailData()[0];
    component.cancelContainerEdit(element);
    expect(showDetailSpy).toHaveBeenCalled();
  });

  it('should unassignUser and refresh details', () => {
    const unassignUserSpy = spyOn(
      containerService,
      'unassignUser',
    ).and.returnValue(of(Object));
    component.userData.set([
      {
        keyMap: { label: 'User Name', key: 'user_name' },
        value: 'bob',
        isEditing: signal(false),
      },
      {
        keyMap: { label: 'User Realm', key: 'user_realm' },
        value: 'realmUser',
        isEditing: signal(false),
      },
    ]);
    component.unassignUser();
    expect(unassignUserSpy).toHaveBeenCalledWith(
      'Mock serial',
      'bob',
      'realmUser',
    );
    expect(component.refreshContainerDetails()).toBeTrue();
  });
});
