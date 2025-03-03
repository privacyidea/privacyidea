import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TokenTableComponent } from './token-table.component';
import { AuthService } from '../../../services/auth/auth.service';
import { TokenService } from '../../../services/token/token.service';
import { Router } from '@angular/router';
import { NotificationService } from '../../../services/notification/notification.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { of } from 'rxjs';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('TokenTableComponent', () => {
  let component: TokenTableComponent;
  let fixture: ComponentFixture<TokenTableComponent>;

  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let tokenServiceSpy: jasmine.SpyObj<TokenService>;
  let routerSpy: jasmine.SpyObj<Router>;
  let notificationServiceSpy: jasmine.SpyObj<NotificationService>;
  let tableUtilsSpy: jasmine.SpyObj<TableUtilsService>;

  beforeEach(async () => {
    authServiceSpy = jasmine.createSpyObj('AuthService', [
      'isAuthenticatedUser',
    ]);
    tokenServiceSpy = jasmine.createSpyObj('TokenService', [
      'apiFilter',
      'advancedApiFilter',
      'getTokenData',
      'toggleActive',
      'resetFailCount',
      'getTokenDetails',
      'setTokenDetail',
      'deleteToken',
    ]);
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    notificationServiceSpy = jasmine.createSpyObj('NotificationService', [
      'openSnackBar',
    ]);
    tableUtilsSpy = jasmine.createSpyObj('TableUtilsService', [
      'toggleKeywordInFilter',
      'parseFilterString',
      'getFilterIconName',
      'getClassForColumnKey',
      'isFilterSelected',
      'isLink',
      'getClassForColumn',
      'getDisplayText',
    ]);

    tokenServiceSpy.apiFilter = [
      'serial',
      'type',
      'active',
      'description',
      'rollout_state',
      'user',
      'tokenrealm',
      'container_serial',
    ];
    tokenServiceSpy.advancedApiFilter = [
      'infokey & infovalue',
      'userid',
      'resolver',
      'assigned',
    ];
    tokenServiceSpy.getTokenData.and.returnValue(
      of({
        result: {
          value: {
            count: 1,
            tokens: [
              {
                id: 1,
                serial: '12345',
                type: 'hotp',
                active: true,
                user: 'test-user',
              },
            ],
          },
        },
      }),
    );
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    routerSpy.navigate.and.returnValue(Promise.resolve(true));

    await TestBed.configureTestingModule({
      imports: [TokenTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceSpy },
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: NotificationService, useValue: notificationServiceSpy },
        { provide: TableUtilsService, useValue: tableUtilsSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTableComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock container');
    component.isProgrammaticChange = signal(false);
    component.selectedContent = signal('token_overview');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('tokenSelected()', () => {
    it('should set tokenSerial and selectedContent, but NOT set isProgrammaticChange', () => {
      expect(component.isProgrammaticChange()).toBeFalse();

      component.tokenSelected('Mock serial');

      expect(component.tokenSerial()).toBe('Mock serial');
      expect(component.selectedContent()).toBe('token_details');
      expect(component.isProgrammaticChange()).toBeFalse();
    });
  });

  describe('containerSelected()', () => {
    it('should set containerSerial, selectedContent, AND set isProgrammaticChange to true', () => {
      expect(component.isProgrammaticChange()).toBeFalse();

      component.containerSelected('Mock serial');

      expect(component.containerSerial()).toBe('Mock serial');
      expect(component.selectedContent()).toBe('container_details');
      expect(component.isProgrammaticChange()).toBeTrue();
    });
  });
});
