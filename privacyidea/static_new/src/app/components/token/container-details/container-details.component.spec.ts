import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal, WritableSignal } from '@angular/core';
import { of } from 'rxjs';

import { ContainerDetailsComponent } from './container-details.component';
import { TokenDetailsComponent } from '../token-details/token-details.component';
import { TokenService } from '../../../services/token/token.service';
import { ContainerService } from '../../../services/container/container.service';
import { ValidateService } from '../../../services/validate/validate.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { UserService } from '../../../services/user/user.service';

function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null),
  };
}

class MockTokenService {
  showOnlyTokenNotInContainer = signal(false);
  tokenSerial = signal('');
  filterValue = signal<Record<string, string>>({});
  pageIndex = signal(0);
  pageSize = signal(10);
  eventPageSize = 10;

  tokenResource = makeResource({
    result: { value: { tokens: [], count: 0 } },
  });

  getTokenDetails = jest.fn().mockReturnValue(of({}));
  getRealms = jest.fn().mockReturnValue(of({ result: { value: [] } }));
  resetFailCount = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  getTokenData = this.getTokenDetails;
}

export class MockContainerService {
  states = signal<string[]>([]);
  containerSerial = signal('Mock serial');

  containerDetailResource = makeResource({
    result: { value: { containers: [] } },
  });

  containerDetail = signal({
    containers: [
      {
        serial: 'Mock serial',
        users: [
          {
            user_realm: 'realmUser',
            user_name: 'bob',
            user_resolver: '',
            user_id: '',
          },
        ],
        realms: [],
        tokens: [],
        type: '',
        states: [],
        description: '',
        select: '',
      },
    ],
    count: 1,
  });

  /* methods touched in tests */
  addTokenToContainer = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  setContainerRealm = jest.fn().mockReturnValue(of(null));
  setContainerDescription = jest.fn().mockReturnValue(of(null));
  deleteAllTokens = jest.fn().mockReturnValue(of(null));
}

class MockValidateService {
  testToken = jest.fn().mockReturnValue(of(null));
}

class MockNotificationService {
  openSnackBar = jest.fn();
}

class MockUserService {
  selectedUserRealm = signal('');
  userFilter = signal('');

  userNameFilter = jest.fn().mockReturnValue('alice');

  setDefaultRealm = jest.fn();
  resetUserSelection = () => {
    this.userFilter.set('');
    this.selectedUserRealm.set('');
  };
}

describe('ContainerDetailsComponent (Jest)', () => {
  let component: ContainerDetailsComponent;
  let fixture: ComponentFixture<ContainerDetailsComponent>;

  let containerService: ContainerService;
  let userService: UserService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: UserService, useClass: MockUserService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock serial');
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
        value: '',
        isEditing: signal(false),
      },
    ]);

    containerService = TestBed.inject(ContainerService);
    userService = TestBed.inject(UserService);

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  it('addTokenToContainer calls service with correct params', () => {
    component.containerSerial = signal('container1');

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

  it('toggles realm edit and saves via setContainerRealm()', () => {
    jest.spyOn(containerService, 'setContainerRealm').mockReturnValue(of({}));

    component.containerDetailData.set([
      {
        keyMap: { label: 'Realms', key: 'realms' },
        value: ['realm1'],
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];

    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBe(true);

    component.selectedRealms.set(['realm1', 'realm2']);
    component.saveContainerEdit(element);

    expect(containerService.setContainerRealm).toHaveBeenCalledWith(
      'Mock serial',
      ['realm1', 'realm2'],
    );
    expect(element.isEditing()).toBe(false);
  });

  it('edits description and calls setContainerDescription()', () => {
    jest
      .spyOn(containerService, 'setContainerDescription')
      .mockReturnValue(of({}));

    component.containerDetailData.set([
      {
        keyMap: { label: 'Description', key: 'description' },
        value: 'Old description',
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];

    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBe(true);

    component.containerDetailData.set([
      {
        keyMap: { label: 'Description', key: 'description' },
        value: 'New description from UI',
        isEditing: signal(false),
      },
    ]);

    component.saveContainerEdit(element);
    expect(containerService.setContainerDescription).toHaveBeenCalledWith(
      'Mock serial',
      'New description from UI',
    );
    expect(element.isEditing()).toBe(false);
  });

  it('enters user edit mode, saves, and exits', () => {
    jest.spyOn(containerService, 'assignUser').mockReturnValue(of({}));

    component.userData.set([
      {
        keyMap: { label: 'User Name', key: 'user_name' },
        value: '',
        isEditing: signal(false),
      },
    ]);
    const element = component.userData()[0];

    expect(component.isEditingUser()).toBe(false);

    component.toggleContainerEdit(element);
    expect(component.isEditingUser()).toBe(true);

    userService.selectedUserRealm.set('realmUser');

    component.saveUser();

    expect(containerService.assignUser).toHaveBeenCalledWith({
      containerSerial: 'Mock serial',
      username: 'alice',
      userRealm: 'realmUser',
    });
    expect(component.isEditingUser()).toBe(false);
  });

  it('canceling a realms edit clears selection', () => {
    component.selectedRealms.set(['realm1']);
    component.containerDetailData.set([
      {
        keyMap: { label: 'Realms', key: 'realms' },
        value: 'irrelevant',
        isEditing: signal(false),
      },
    ]);
    const element = component.containerDetailData()[0];
    component.cancelContainerEdit(element);

    expect(component.selectedRealms()).toEqual([]);
  });

  it('unassignUser triggers service and refresh', () => {
    jest.spyOn(containerService, 'unassignUser').mockReturnValue(of({}));

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

    expect(containerService.unassignUser).toHaveBeenCalledWith(
      'Mock serial',
      'bob',
      'realmUser',
    );
  });
});
